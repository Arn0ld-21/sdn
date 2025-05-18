import random
import simpy
import statistics
from telemetry_collector_ContrrolPlane import TelemetryCollector
from qllb_controller_ControlPlane import QLLBController


random.seed(42)


class Link:
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
            svc = random.expovariate(self.rate) * (pkt["size"] / 1000)
            yield self.env.timeout(svc)
            pkt["depart_time"] = self.env.now
            self.packets -= 1
            print(f"{self.env.now:.2f}s: Link {self.id} sent {pkt['id']} to sink")
            yield pkt["sink"].put(pkt)

    def put(self, pkt):
        self.packets += 1
        pkt["enter_time"] = self.env.now
        print(
            f"{self.env.now:.2f}s: Packet {pkt['id']} enqueued on {self.id} (Q={self.packets})"
        )
        return self.store.put(pkt)

    def queue_length(self):
        return self.packets


class LeafSwitch:
    def __init__(self, env, name, spines):
        self.env = env
        self.name = name
        self.spines = spines

    def put(self, pkt, spine):
        return spine.put(pkt)


class Host:
    def __init__(self, env, name, controller, sink, flow_rate, count, pkt_size_range):
        self.env = env
        self.name = name
        self.controller = controller
        self.sink = sink
        self.flow_rate = flow_rate
        self.count = count
        self.pkt_size_range = pkt_size_range
        env.process(self.generate())

    def generate(self):
        for i in range(self.count):
            yield self.env.timeout(random.expovariate(self.flow_rate))
            size = random.randint(*self.pkt_size_range)
            pkt = {
                "id": f"{self.name}-{i}",
                "src": self,
                "sink": self.sink,
                "start": self.env.now,
                "size": size,
            }
            print(
                f"{self.env.now:.2f}s: Host {self.name} generated {pkt['id']} (size={size}B)"
            )
            self.env.process(self.controller.dispatch(pkt))


class Sink:
    def __init__(self, env):
        self.env = env
        self.store = simpy.Store(env)

    def put(self, pkt):
        return self.store.put(pkt)

    def get(self):
        return self.store.get()


class SimpleAdapter:
    def __init__(self, leaves):
        self.leaves = {leaf.name: leaf for leaf in leaves}

    def get_queue_stats(self, sw_name):
        leaf = self.leaves[sw_name]
        return {i + 1: sp.queue_length() for i, sp in enumerate(leaf.spines)}

    def get_port_stats(self, sw_name):
        return {}

    def get_flow_stats(self, sw_name):
        return {}


def simple_emulation(
    num_flows=100, flow_rate=5.0, sim_time=10, num_leaves=4, pkt_size_range=(500, 1500)
):
    """
        num_flows=100: скільки пакетів генерує кожний host.
        flow_rate=5.0: середня інтенсивність (λ) 5 пакетів/с.
        pkt_size_range=(500,1500): розміри від 500 до 1500 байт.
        sim_time=60: симуляція 60 секунд.
        num_leaves=4: відповідає вашій топології із 4 Leaf + 4 Hosts.
    """
    env = simpy.Environment()
    sink = Sink(env)

    spines = [Link(env, rate=20, id=f"s{i+1}") for i in range(2)]
    leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]

    adapter = SimpleAdapter(leaves)
    tc = TelemetryCollector(adapter, sample_interval=0.2)

    controller = QLLBController(env, leaves, spines, telemetry_collector=tc, qmax=100)

    for i, leaf in enumerate(leaves, start=1):
        h = Host(env, f"h{i}", controller, sink, flow_rate, num_flows, pkt_size_range)
        h.leaf = leaf

    print(">>> Starting emulation")
    env.run(until=sim_time)
    print(">>> Emulation complete\n")

    # Короткий лог фінальних метрик
    print("=== Final telemetry ===")
    print(
        "Avg Queue Length per leaf:",
        {leaf: tc.compute_aql(leaf) for leaf in tc.queue_history},
    )
    print("Avg Latency:", tc.compute_al())
    print("Packet Loss Rate:", tc.compute_plr())
    print(
        "Channel Utilization per leaf:",
        {leaf: tc.compute_cu(leaf) for leaf in tc.util_history},
    )


if __name__ == "__main__":
    simple_emulation()
