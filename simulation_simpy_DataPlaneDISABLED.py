# Оновлений simulation_simpy.py з поверненням результатів замість друку

"""
simulation_simpy.py: Симпліфікована симуляція QLLB на Windows за допомогою SimPy.
Топологія leaf–spine, метрики latency.
"""

import simpy
import random
import statistics


class Link:
    def __init__(self, env, rate):
        self.env = env
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


class Host:
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
            self.env.process(self.controller.dispatch(flow))


class QLLBController:
    def __init__(self, env, leaves, spines):
        self.env = env
        self.leaves = leaves
        self.spines = spines
        self.metrics = []

    def dispatch(self, pkt):
        leaf = pkt["src"].leaf
        spine = min(self.spines, key=lambda s: s.queue_length())
        yield leaf.put(pkt, spine)
        rec_pkt = yield pkt["sink"].get()
        latency = rec_pkt["depart_time"] - rec_pkt["start"]
        self.metrics.append(latency)


class LeafSwitch:
    def __init__(self, env, name, spines):
        self.env = env
        self.name = name
        self.spines = spines

    def put(self, pkt, spine):
        return spine.put(pkt)


class Sink:
    def __init__(self, env):
        self.env = env
        self.store = simpy.Store(env)

    def put(self, pkt):
        return self.store.put(pkt)

    def get(self):
        return self.store.get()


# def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100):
#     env = simpy.Environment()
#     sink = Sink(env)
#     spines = [Link(env, rate=10) for _ in range(2)]
#     leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(2)]
#     controller = QLLBController(env, leaves, spines)
#     hosts = [
#         Host(env, f"h{i+1}", controller, sink, flow_rate, num_flows) for i in range(2)
#     ]
#     for h, leaf in zip(hosts, leaves):
#         h.leaf = leaf

#     env.run(until=sim_time)

#     # Повернення середньої затримки та 95-го перцентиля
#     if controller.metrics:
#         mean_latency = statistics.mean(controller.metrics)
#         p95_latency = statistics.quantiles(controller.metrics, n=20)[18]
#     else:
#         mean_latency = None
#         p95_latency = None

#     return mean_latency, p95_latency


def run_simulation(num_flows=50, flow_rate=0.5, sim_time=100, num_leaves=4):
    env = simpy.Environment()
    sink = Sink(env)
    spines = [Link(env, rate=10) for _ in range(2)]
    # Створюємо num_leaves leaf-комутаторів
    leaves = [LeafSwitch(env, f"leaf{i+1}", spines) for i in range(num_leaves)]
    controller = QLLBController(env, leaves, spines)
    # Складемо по одному host на кожен leaf
    hosts = []
    for i, leaf in enumerate(leaves, start=1):
        h = Host(env, f"h{i}", controller, sink, flow_rate, num_flows)
        h.leaf = leaf
        hosts.append(h)
    # Запускаємо симуляцію
    env.run(until=sim_time)

    # Повернення середньої затримки та 95-го перцентиля
    if controller.metrics:
        mean_latency = statistics.mean(controller.metrics)
        p95_latency = statistics.quantiles(controller.metrics, n=20)[18]
    else:
        mean_latency = None
        p95_latency = None

    return mean_latency, p95_latency


if __name__ == "__main__":
    m, p95 = run_simulation()
    print("Mean latency:", m)
    print("95th percentile latency:", p95)
