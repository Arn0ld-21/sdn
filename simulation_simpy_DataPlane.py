# Updated simulation_simpy.py integrating TelemetryCollector and QLLBController

"""
simulation_simpy.py: Симуляція QLLB з повною інтеграцією TelemetryCollector.
Leaf–Spine топологія відповідно до опису.
"""

import simpy
import random
import statistics

from telemetry_collector_ContrrolPlane import TelemetryCollector
from qos_classifier_ApplicationPlane import QoSClassifier
from qllb_controller_ControlPlane import QLLBController

# # Фіксимо seed для відтворюваності
# random.seed(42)


# class Link:
#     """Модель лінку з M/M/1 чергою."""

#     def __init__(self, env, rate, id):
#         self.env = env
#         self.id = id
#         self.rate = rate
#         self.store = simpy.Store(env)
#         self.packets = 0
#         env.process(self.serve())

#     def serve(self):
#         while True:
#             pkt = yield self.store.get()
#             yield self.env.timeout(random.expovariate(self.rate))
#             pkt["depart_time"] = self.env.now
#             self.packets -= 1
#             yield pkt["sink"].put(pkt)

#     def put(self, pkt):
#         self.packets += 1
#         pkt["enter_time"] = self.env.now
#         return self.store.put(pkt)

#     def queue_length(self):
#         return self.packets


# class LeafSwitch:
#     """Leaf-комутатор, що пересилає до spine лінків."""

#     def __init__(self, env, name, spines):
#         self.env = env
#         self.name = name
#         self.spines = spines

#     def put(self, pkt, spine):
#         return spine.put(pkt)


# class Host:
#     """Генератор потоків із викликом controller.dispatch."""

#     def __init__(self, env, name, controller, sink, flow_rate, count):
#         self.env = env
#         self.name = name
#         self.controller = controller
#         self.sink = sink
#         self.flow_rate = flow_rate
#         self.count = count
#         env.process(self.generate())

#     def generate(self):
#         for i in range(self.count):
#             yield self.env.timeout(random.expovariate(self.flow_rate))
#             flow = {
#                 "id": f"{self.name}-{i}",
#                 "src": self,
#                 "sink": self.sink,
#                 "start": self.env.now,
#             }
#             # Контролер повертає порт, ми передаємо LeafSwitch.put
#             port, spine = self.controller.dispatch(
#                 flow,
#                 self.src_leaf.name,
#                 {idx + 1: spine for idx, spine in enumerate(self.src_leaf.spines)},
#             )
#             # Виконати передачу через обраний порт
#             yield self.src_leaf.put(flow, spine)


# class Sink:
#     """Приймальний вузол для завершених пакетів."""

#     def __init__(self, env):
#         self.env = env
#         self.store = simpy.Store(env)

#     def put(self, pkt):
#         return self.store.put(pkt)

#     def get(self):
#         return self.store.get()


# # Адаптер для TelemetryCollector у симуляції
# class SimulationAdapter:
#     def __init__(self, leaves, spines, controller):
#         self.leaves = {leaf.name: leaf for leaf in leaves}
#         self.spines = spines
#         self.controller = controller

#     def get_queue_stats(self, sw_name):
#         leaf = self.leaves[sw_name]
#         # повернути довжини черг spine-лінків
#         return {
#             port: spine.queue_length()
#             for port, spine in enumerate(leaf.spines, start=1)
#         }

#     def get_port_stats(self, sw_name):
#         # для симуляції не використовуємо через байти, повертаємо пусто
#         return {port: {"tx_bytes": 0} for port in range(1, len(self.spines) + 1)}

#     def get_flow_stats(self, sw_name):
#         # повернути втрати та латенси, які controller.metrics зберігає окремо
#         stats = {}
#         # немає індивідуальних flow stats у симуляції
#         return stats

#     def install_flow(self, sw_name, flow_id, port):
#         # симуляція не потребує реальних FlowMod
#         pass


# def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100, num_leaves=4):
#     env = simpy.Environment()
#     sink = Sink(env)
#     # створюємо spine лінки
#     spines = [Link(env, rate=10, id=f"s{i+1}") for i in range(2)]
#     # створюємо leaf-комутатори
#     leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]
#     # TelemetryCollector та QLLBController
#     adapter = SimulationAdapter(leaves, spines, None)
#     tc = TelemetryCollector(adapter, sample_interval=0.1)
#     qos = QoSClassifier()
#     controller = QLLBController([adapter], tc, qos_classifier=qos, qmax=100)
#     # додаємо контролеру посилання на leaf у хости
#     hosts = []
#     for leaf in leaves:
#         h = Host(env, f"h{leaf.name[-1]}", controller, sink, flow_rate, num_flows)
#         h.src_leaf = leaf
#         hosts.append(h)
#     # періодичний збір телеметрії
#     env.process(
#         lambda: (tc.periodic_collection([leaf.name for leaf in leaves], sim_time))
#         # tc.periodic_collection([leaf.name for leaf in leaves], sim_time)
#     )
#     # запуск симуляції
#     env.run(until=sim_time)
#     # повернути метрики
#     return tc.compute_al(), None


# if __name__ == "__main__":
#     m, _ = run_simulation()
#     print("Average Latency (from Telemetry):", m)


# ================================================================================================================
# ================================================================================================================
# ================================================================================================================
# ================================================================================================================


# Фіксимо seed для відтворюваності
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
    """Генератор потоків із викликом controller.dispatch."""

    def __init__(self, env, name, controller, sink, flow_rate, count):
        self.env = env
        self.name = name
        self.controller = controller
        self.sink = sink
        self.flow_rate = flow_rate
        self.count = count
        env.process(self.generate())

    def generate(self):
        for i in range(self.count):
            yield self.env.timeout(random.expovariate(self.flow_rate))
            flow = {
                "id": f"{self.name}-{i}",
                "src": self,
                "sink": self.sink,
                "start": self.env.now,
            }
            # Контролер повертає порт, ми передаємо LeafSwitch.put
            port, spine = self.controller.dispatch(
                flow,
                self.src_leaf.name,
                {idx + 1: spine for idx, spine in enumerate(self.src_leaf.spines)},
            )
            # Виконати передачу через обраний порт
            yield self.src_leaf.put(flow, spine)


class Sink:
    """Приймальний вузол для завершених пакетів."""

    def __init__(self, env):
        self.env = env
        self.store = simpy.Store(env)

    def put(self, pkt):
        return self.store.put(pkt)

    def get(self):
        return self.store.get()


# Адаптер для TelemetryCollector у симуляції
class SimulationAdapter:
    def __init__(self, leaves, spines, controller):
        self.leaves = {leaf.name: leaf for leaf in leaves}
        self.spines = spines
        self.controller = controller

    def get_queue_stats(self, sw_name):
        leaf = self.leaves[sw_name]
        # повернути довжини черг spine-лінків
        return {
            port: spine.queue_length()
            for port, spine in enumerate(leaf.spines, start=1)
        }

    def get_port_stats(self, sw_name):
        # для симуляції не використовуємо через байти, повертаємо пусто
        return {port: {"tx_bytes": 0} for port in range(1, len(self.spines) + 1)}

    def get_flow_stats(self, sw_name):
        # повернути втрати та латенси, які controller.metrics зберігає окремо
        stats = {}
        # немає індивідуальних flow stats у симуляції
        return stats

    def install_flow(self, sw_name, flow_id, port):
        # симуляція не потребує реальних FlowMod
        pass


class SimpyAdapter:
    """Адаптер до TelemetryCollector для SimPy-топології."""

    def __init__(self, leaves):
        # leaves: список LeafSwitch
        self.leaves = {leaf.name: leaf for leaf in leaves}

    def get_queue_stats(self, switch_id):
        leaf = self.leaves[switch_id]
        # портам spine відповідають індекси 1..len(spines)
        return {i + 1: sp.queue_length() for i, sp in enumerate(leaf.spines)}

    def get_port_stats(self, switch_id):
        # не використовується в SimPy
        return {}

    def get_flow_stats(self, switch_id):
        # не використовується тут
        return {}


# Ваші класи Link, Host, LeafSwitch, Sink залишаються без змін


def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100, num_leaves=4):
    env = simpy.Environment()
    sink = Sink(env)

    # створюємо spine та leaf
    # spines = [Link(env, rate=10) for _ in range(2)]
    spines = [Link(env, rate=10, id=f"s{i+1}") for i in range(2)]
    leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]

    # Telemetry + адаптер
    adapter = SimpyAdapter(leaves)
    tc = TelemetryCollector(adapter, sample_interval=0.1)

    # контролер тепер приймає tc
    controller = QLLBController(env, leaves, spines, telemetry_collector=tc, qmax=100)

    # hosts
    hosts = []
    for i, leaf in enumerate(leaves, start=1):
        h = Host(env, f"h{i}", controller, sink, flow_rate, num_flows)
        h.leaf = leaf
        hosts.append(h)

    # запустити симуляцію
    env.run(until=sim_time)

    # Повернемо основні метрики
    mean_latency = statistics.mean(controller.metrics) if controller.metrics else None
    p95_latency = (
        statistics.quantiles(controller.metrics, n=20)[18]
        if controller.metrics
        else None
    )

    # А також обчислювальні похідні
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


# def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100, num_leaves=4):
#     env = simpy.Environment()
#     sink = Sink(env)
#     # створюємо spine лінки
#     spines = [Link(env, rate=10, id=f"s{i+1}") for i in range(2)]
#     # створюємо leaf-комутатори
#     leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]
#     # TelemetryCollector та QLLBController
#     adapter = SimulationAdapter(leaves, spines, None)
#     tc = TelemetryCollector(adapter, sample_interval=0.1)
#     qos = QoSClassifier()
#     controller = QLLBController([adapter], tc, qos_classifier=qos, qmax=100)
#     # додаємо контролеру посилання на leaf у хости
#     hosts = []
#     for leaf in leaves:
#         h = Host(env, f"h{leaf.name[-1]}", controller, sink, flow_rate, num_flows)
#         h.src_leaf = leaf
#         hosts.append(h)
#     # періодичний збір телеметрії
#     env.process(
#         lambda: (tc.periodic_collection([leaf.name for leaf in leaves], sim_time))
#         # tc.periodic_collection([leaf.name for leaf in leaves], sim_time)
#     )
#     # запуск симуляції
#     env.run(until=sim_time)
#     # повернути метрики
#     return tc.compute_al(), None


if __name__ == "__main__":
    m, _ = run_simulation()
    print("Average Latency (from Telemetry):", m)
