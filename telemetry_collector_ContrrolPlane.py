# telemetry_collector.py: модуль для збору статистики з SDN-комутаторів через OpenFlow

"""
telemetry_collector.py: Збирає статистику черг, портів і потоків з контролера SDN.
"""

import time


class TelemetryCollector:
    """
    Збирає та зберігає статистику з OpenFlow-комутаторів:
      - queue length (черги)
      - port utilization (завантаження)
      - flow statistics (загальні метрики потоків)
    Використовує адаптери до OpenDaylight та/або ONOS.
    """

    def __init__(self, odl_adapter, onos_adapter=None, sample_interval=1.0):
        """
        odl_adapter: екземпляр ODLAdapter
        onos_adapter: опціональний екземпляр ONOSAdapter
        sample_interval: інтервал між опитуваннями в секундах
        """
        self.odl = odl_adapter
        self.onos = onos_adapter
        self.interval = sample_interval
        self.queue_stats = {}  # {switch_id: {queue_id: length}}
        self.port_stats = {}  # {switch_id: {port_no: utilization}}
        self.flow_stats = {}  # {flow_id: {metrics}}

    def collect_queue_stats(self, switch_id):
        """
        Опитує черги конкретного комутатора.
        Повертає словник {queue_id: queue_length}.
        """
        stats = self.odl.get_queue_stats(switch_id)
        # При потребі можна комбінувати з ONOSAdapter:
        if self.onos:
            stats_onos = self.onos.get_queue_stats(switch_id)
            stats.update(stats_onos)
        self.queue_stats[switch_id] = stats
        return stats

    def collect_port_stats(self, switch_id):
        """
        Опитує статистику портів конкретного комутатора.
        Повертає {port_no: {'tx_bytes': ..., 'rx_bytes': ..., 'utilization': ...}}.
        """
        stats = self.odl.get_port_stats(switch_id)
        if self.onos:
            stats_onos = self.onos.get_port_stats(switch_id)
            stats.update(stats_onos)
        # Розрахувати utilization якщо задано к-ть байт та interval
        for port, data in stats.items():
            tx = data.get("tx_bytes", 0)
            utilization = (
                (tx * 8) / (self.interval * 1e8) * 100
            )  # assuming 100Mb/s link
            data["utilization"] = utilization
        self.port_stats[switch_id] = stats
        return stats

    def collect_flow_stats(self, switch_id):
        """
        Опитує загальні метрики потоків (FLOW_STATS).
        Повертає {flow_id: {'packets': ..., 'packet_loss': ..., 'latency': ...}}.
        """
        stats = self.odl.get_flow_stats(switch_id)
        if self.onos:
            stats_onos = self.onos.get_flow_stats(switch_id)
            stats.update(stats_onos)
        # Обчислити packet_loss, latency за flow metrics
        for flow, data in stats.items():
            sent = data.get("packets_sent", 0)
            recv = data.get("packets_received", sent)
            loss = (sent - recv) / sent if sent else 0.0
            data["packet_loss"] = loss
            # latency має бути отримана окремо чи через RTT probe
        self.flow_stats[switch_id] = stats
        return stats

    def collect_all(self, switch_ids):
        """
        Опитує всі вказані комутатори.
        Повертає сумарні словники всіх метрик.
        """
        for sw in switch_ids:
            self.collect_queue_stats(sw)
            self.collect_port_stats(sw)
            self.collect_flow_stats(sw)
        return {
            "queues": self.queue_stats,
            "ports": self.port_stats,
            "flows": self.flow_stats,
        }

    def periodic_collection(self, switch_ids, duration):
        """
        Періодичний збір протягом duration секунд.
        """
        end_time = time.time() + duration
        while time.time() < end_time:
            self.collect_all(switch_ids)
            time.sleep(self.interval)


# Тестова перевірка (псевдозаміри)
if __name__ == "__main__":

    class DummyAdapter:
        def get_queue_stats(self, sw):
            return {0: 5, 1: 3}

        def get_port_stats(self, sw):
            return {1: {"tx_bytes": 1250000}, 2: {"tx_bytes": 2500000}}

        def get_flow_stats(self, sw):
            return {"flow1": {"packets_sent": 100, "packets_received": 95}}

    odl = DummyAdapter()
    tc = TelemetryCollector(odl, None, sample_interval=0.5)
    data = tc.collect_all(["s1", "s2"])
    print(data)
