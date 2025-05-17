# qllb_controller.py
from qos_classifier_ApplicationPlane import QoSClassifier
from telemetry_collector_ContrrolPlane import TelemetryCollector


# class QLLBController:
#     """
#     Контролер QLLB:
#       - Збирає метрики через TelemetryCollector
#       - Отримує ваги через QoSClassifier
#       - Вибирає вихідний порт за функцією корисності U(Q,W,R)

#       - adapters: список адаптерів (ODL/ONOS/SimulationAdapter)
#       - telemetry_collector: TelemetryCollector
#       - qos_classifier: QoSClassifier
#       - qmax: max queue length для нормалізації
#     """

#     def __init__(self, adapters, telemetry_collector, qos_classifier=None, qmax=100):
#         """
#         telemetry_collector: інстанс TelemetryCollector
#         qos_classifier: інстанс QoSClassifier (якщо None — створиться новий)
#         qmax: нормалізаційне max-значення для черг
#         """
#         self.adapters = adapters
#         self.tc = telemetry_collector
#         self.qc = qos_classifier or QoSClassifier()
#         self.qmax = qmax

#     def select_route(self, pkt, switch_id, out_ports):
#         """
#         pkt: dict з ключем 'id' (ідентифікатор потоку)
#         switch_id: ID leaf-комутатора, де обираємо порт
#         out_ports: {port_no: опис} — потенційні вихідні порти
#         Повертає вибраний port_no.
#         """
#         # 1) Збір актуальної телеметрії
#         queues = self.tc.collect_queue_stats(switch_id)
#         flows = self.tc.collect_flow_stats(switch_id)
#         ports = self.tc.collect_port_stats(switch_id)

#         # 2) Ваги QoS для цього потоку
#         weights = self.qc.get_weights(pkt)
#         wQ, wW, wR = weights["w_Q"], weights["w_W"], weights["w_R"]

#         # 3) Шукаємо max U
#         best_port, best_u = None, -float("inf")
#         for port, desc in out_ports.items():
#             Q = queues.get(port, 0)
#             flow_data = flows.get(pkt["id"], {})
#             W = flow_data.get("latency", 1.0)  # сек
#             R = 1.0 - flow_data.get("packet_loss", 0.0)  # безрозм

#             U = wQ * (1 - Q / self.qmax) + wW * (1.0 / (W + 1e-6)) + wR * R
#             if U > best_u:
#                 best_u, best_port = U, port

#         return best_port

#     # def dispatch(self, pkt, switch_id, out_ports):
#     #     """
#     #     Вибирає порт і повертає його для подальшої обробки (наприклад, симулятором або ODLAdapter).
#     #     """
#     #     port = self.select_route(pkt, switch_id, out_ports)
#     #     return port

#     def dispatch(self, pkt, switch_id, out_ports):
#         port = self.select_route(pkt, switch_id, out_ports)
#         # в Mininet-режимі тут ви перебираєте adapters[i].install_flow(...)
#         # в симуляції цей метод може бути заглушкою
#         for adapter in self.adapters:
#             adapter.install_flow(switch_id, pkt["id"], port)
#         return port


# # ---------- Приклад перевірки ----------
# if __name__ == "__main__":
#     # Простий "заглушковий" телеметричний адаптер
#     class DummyAdapter:
#         def get_queue_stats(self, sw):
#             return {1: 20, 2: 5}

#         def get_port_stats(self, sw):
#             return {1: {"tx_bytes": 1000}, 2: {"tx_bytes": 2000}}

#         def get_flow_stats(self, sw):
#             return {
#                 "flowA": {"packets_sent": 100, "packets_received": 90, "latency": 0.1}
#             }

#     # Ініціалізація
#     tc = TelemetryCollector(DummyAdapter())
#     from qos_classifier_ApplicationPlane import QoSClassifier

#     qc = QoSClassifier()
#     controller = QLLBController(tc, qc, qmax=100)

#     # Тестовий потік
#     pkt = {"id": "flowA"}
#     chosen = controller.dispatch(pkt, switch_id="leaf1", out_ports={1: "s1", 2: "s2"})
#     print(f"Chosen port for {pkt['id']}: {chosen}")


##############
# Update to connect TelemetryCollector ↔ QLLBController
##################


# qllb_controller.py

# from qos_classifier import QoSClassifier
# from telemetry_collector import TelemetryCollector


class QLLBController:
    """
    Контролер QLLB із підтримкою TelemetryCollector
    """

    def __init__(self, env, leaves, spines, telemetry_collector, qmax=100):
        self.env = env
        self.leaves = leaves
        self.spines = spines
        self.tc = telemetry_collector  # <-- сюди
        self.qc = QoSClassifier()
        self.qmax = qmax
        self.metrics = []  # для спостереження latency в simpy

    def select_route(self, pkt, leaf_switch):
        # Збираємо телеметрію перед вибором
        self.tc.collect_queue_stats(leaf_switch.name)
        # (можна також self.tc.collect_port_stats та collect_flow_stats)

        queues = self.tc.queue_stats[leaf_switch.name]
        weights = self.qc.get_weights(pkt)
        wQ, wW, wR = weights["w_Q"], weights["w_W"], weights["w_R"]

        best_port = None
        best_u = -float("inf")
        for idx, spine in enumerate(leaf_switch.spines, start=1):
            Q = queues.get(idx, 0)
            # У SimPy ми ще не інтегрували W, R у Telemetry:
            W, R = 1.0, 1.0
            U = wQ * (1 - Q / self.qmax) + wW * (1 / (W + 1e-6)) + wR * R
            if U > best_u:
                best_u, best_port = U, idx
        return best_port

    def dispatch(self, pkt):
        leaf = pkt["src"].leaf
        port_idx = self.select_route(pkt, leaf)
        spine = leaf.spines[port_idx - 1]

        # forward
        yield leaf.put(pkt, spine)

        # дораховуємо delay
        rec_pkt = yield pkt["sink"].get()
        latency = rec_pkt["depart_time"] - rec_pkt["start"]
        self.metrics.append(latency)

        # Додаємо latency в телеметрію
        # (Навіть якщо виклик не потрібний для вибору маршруту, він записує дані в tc)
        # Ми зімітуємо виклик:
        self.tc.latency_samples.append(latency)
