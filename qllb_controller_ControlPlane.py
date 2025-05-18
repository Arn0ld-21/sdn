from qos_classifier_ApplicationPlane import QoSClassifier
from qos_classifier_ApplicationPlane import QoSClassifier
from telemetry_collector_ContrrolPlane import TelemetryCollector


class QLLBController:
    """
    Контролер QLLB із підтримкою TelemetryCollector,
    FlowMod-затримкою та кастомним QoSClassifier.
    """

    def __init__(
        self,
        env,
        leaves,
        spines,
        telemetry_collector,
        qmax=100,
        flowmod_delay=0.0,
        qos_classifier=None,
    ):
        self.env = env
        self.leaves = leaves
        self.spines = spines
        self.tc = telemetry_collector
        self.qmax = qmax
        self.flowmod_delay = flowmod_delay
        # Використати кастомний класифікатор або дефолтний
        self.qc = qos_classifier if qos_classifier is not None else QoSClassifier()
        self.metrics = []  # для збору latency

    def select_route(self, pkt, leaf_switch):
        # Зібрати телеметрію черги
        self.tc.collect_queue_stats(leaf_switch.name)

        queues = self.tc.queue_stats[leaf_switch.name]
        weights = self.qc.get_weights(pkt)
        wQ, wW, wR = weights["w_Q"], weights["w_W"], weights["w_R"]

        best_port = None
        best_u = -float("inf")
        for idx, spine in enumerate(leaf_switch.spines, start=1):
            Q = queues.get(idx, 0)
            # Використовуємо заглушкові W,R
            W, R = 1.0, 1.0
            U = wQ * (1 - Q / self.qmax) + wW * (1 / (W + 1e-6)) + wR * R
            if U > best_u:
                best_u, best_port = U, idx
        return best_port

    def dispatch(self, pkt):
        leaf = pkt["src"].leaf
        port_idx = self.select_route(pkt, leaf)
        spine = leaf.spines[port_idx - 1]

        # Імітація FlowMod-затримки
        if self.flowmod_delay > 0:
            yield self.env.timeout(self.flowmod_delay)

        # Передача пакету по обраному spine
        yield leaf.put(pkt, spine)

        # Очікуємо доставку в sink
        rec_pkt = yield pkt["sink"].get()
        latency = rec_pkt["depart_time"] - rec_pkt["start"]
        self.metrics.append(latency)
        # Запис latency у телеметрію
        self.tc.latency_samples.append(latency)
