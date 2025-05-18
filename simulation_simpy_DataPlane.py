import random
import statistics
import simpy


from telemetry_collector_ContrrolPlane import TelemetryCollector
from qos_classifier_ApplicationPlane import QoSClassifier
from qllb_controller_ControlPlane import QLLBController


# Фіксуємо seed для відтворюваності
random.seed(42)


class Link:
    """Модель лінку з M/M/1 чергою."""

    def __init__(self, env, rate, id):
        self.env = env
        self.id = id
        self.rate = rate
        self.store = simpy.Store(env)
        self.packets = 0
        env.process(self.serve())

    def serve(self):
        while True:
            pkt = yield self.store.get()
            yield self.env.timeout(random.expovariate(self.rate))
            pkt["depart_time"] = self.env.now
            self.packets -= 1
            # Кладемо в Sink
            yield pkt["sink"].put(pkt)

    def put(self, pkt):
        self.packets += 1
        pkt["enter_time"] = self.env.now
        return self.store.put(pkt)

    def queue_length(self):
        return self.packets


class LeafSwitch:
    """Leaf-комутатор, що пересилає до spine лінків."""

    def __init__(self, env, name, spines):
        self.env = env
        self.name = name
        self.spines = spines

    def put(self, pkt, spine):
        return spine.put(pkt)


class Host:
    """Генератор потоків — просто тригерить dispatch у контролері."""

    def __init__(self, env, name, controller, sink, flow_rate, count):
        self.env = env
        self.name = name
        self.controller = controller
        self.sink = sink
        self.flow_rate = flow_rate
        self.count = count
        # Потік генерації
        env.process(self.generate())

    def generate(self):
        for i in range(self.count):
            # Інтервали між пакетами за пуассонівською моделлю
            yield self.env.timeout(random.expovariate(self.flow_rate))
            flow = {
                "id": f"{self.name}-{i}",
                "src": self,
                "sink": self.sink,
                "start": self.env.now,
            }
            # Запускаємо dispatch як окремий процес
            self.env.process(self.controller.dispatch(flow))


class Sink:
    """Приймальний вузол для завершених пакетів."""

    def __init__(self, env):
        self.env = env
        self.store = simpy.Store(env)

    def put(self, pkt):
        return self.store.put(pkt)

    def get(self):
        return self.store.get()


class SimpyAdapter:
    """Адаптер до TelemetryCollector для SimPy-топології."""

    def __init__(self, leaves):
        # Для опитування черг
        self.leaves = {leaf.name: leaf for leaf in leaves}

    def get_queue_stats(self, switch_id):
        leaf = self.leaves[switch_id]
        # портам spine відповідають індекси 1..len(spines)
        return {i + 1: sp.queue_length() for i, sp in enumerate(leaf.spines)}

    def get_port_stats(self, switch_id):
        # не використовується в SimPy
        return {}

    def get_flow_stats(self, switch_id):
        # не використовується в SimPy
        return {}


def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100, num_leaves=4):
    env = simpy.Environment()
    sink = Sink(env)

    # 1) spine-лінки
    spines = [Link(env, rate=10, id=f"s{i+1}") for i in range(2)]
    # 2) leaf-комутатори
    leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]

    # 3) TelemetryCollector із SimpyAdapter
    adapter = SimpyAdapter(leaves)
    tc = TelemetryCollector(adapter, sample_interval=0.1)

    # 4) Контролер з підключеним TelemetryCollector
    controller = QLLBController(env, leaves, spines, telemetry_collector=tc, qmax=100)

    # 5) hosts, прив'язуємо кожному його leaf
    for i, leaf in enumerate(leaves, start=1):
        h = Host(env, f"h{i}", controller, sink, flow_rate, num_flows)
        h.leaf = leaf  # <--- важливо, тепер generate() використовує h.leaf
    # 6) Запуск
    env.run(until=sim_time)

    # 7) Збір та повернення метрик
    mean_latency = statistics.mean(controller.metrics) if controller.metrics else None
    p95_latency = (
        statistics.quantiles(controller.metrics, n=20)[18]
        if controller.metrics
        else None
    )
    # Похідні метрики з TelemetryCollector
    aql = {leaf.name: tc.compute_aql(leaf.name) for leaf in leaves}
    al = tc.compute_al()
    plr = tc.compute_plr()
    cu = {leaf.name: tc.compute_cu(leaf.name) for leaf in leaves}

    return {
        "mean_latency": mean_latency,
        "p95_latency": p95_latency,
        "average_queue_length": aql,
        "average_latency": al,
        "packet_loss_rate": plr,
        "channel_utilization": cu,
    }


if __name__ == "__main__":
    results = run_simulation()
    print("Simulation results:", results)
