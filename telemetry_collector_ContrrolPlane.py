# Updated telemetry_collector.py with metric histories and computation methods

"""
telemetry_collector.py: Enhanced TelemetryCollector for SDN experiments.
Collects queue length, port utilization, flow latency and packet loss;
stores history and computes AQL, AL, PLR, CU.
"""

import time
from collections import defaultdict
import statistics


class TelemetryCollector:
    """
    Collects and processes telemetry from SDN switches via adapters.
    """

    def __init__(self, odl_adapter, onos_adapter=None, sample_interval=0.1):
        """
        odl_adapter: instance of ODLAdapter
        onos_adapter: optional instance of ONOSAdapter
        sample_interval: sampling period in seconds (default 100ms)
        """
        self.odl = odl_adapter
        self.onos = onos_adapter
        self.interval = sample_interval

        # Raw latest stats
        self.queue_stats = {}  # {sw: {queue_id: length}}
        self.port_stats = {}  # {sw: {port_no: {..., utilization:%}}}
        self.flow_stats = {}  # {sw: {flow_id: {...}}}

        # Histories for derived metrics
        self.queue_history = defaultdict(list)  # {sw: [avgQ1, avgQ2, ...]}
        self.util_history = defaultdict(list)  # {sw: [avgUtil1, avgUtil2, ...]}
        self.latency_samples = []  # [latency1, latency2, ...]
        self.loss_samples = []  # [ploss1, ploss2, ...]

    def collect_queue_stats(self, switch_id):
        """
        Poll queue lengths; update history.
        """
        stats = self.odl.get_queue_stats(switch_id)
        if self.onos:
            stats.update(self.onos.get_queue_stats(switch_id))
        self.queue_stats[switch_id] = stats

        # Compute average queue length across all queues
        if stats:
            avg_q = statistics.mean(stats.values())
            self.queue_history[switch_id].append(avg_q)
        return stats

    def collect_port_stats(self, switch_id):
        """
        Poll port stats and compute utilization; update history.
        """
        stats = self.odl.get_port_stats(switch_id)
        if self.onos:
            stats.update(self.onos.get_port_stats(switch_id))
        # Compute utilization and update history
        utils = []
        for port, data in stats.items():
            tx = data.get("tx_bytes", 0)
            # Assume link capacity 100 Mbps
            util = (tx * 8) / (self.interval * 1e8) * 100
            data["utilization"] = util
            utils.append(util)
        self.port_stats[switch_id] = stats

        if utils:
            avg_util = statistics.mean(utils)
            self.util_history[switch_id].append(avg_util)
        return stats

    def collect_flow_stats(self, switch_id):
        """
        Poll flow stats; compute packet loss and latency; update samples.
        """
        stats = self.odl.get_flow_stats(switch_id)
        if self.onos:
            stats.update(self.onos.get_flow_stats(switch_id))
        losses = []
        lats = []
        for flow, data in stats.items():
            sent = data.get("packets_sent", 0)
            recv = data.get("packets_received", sent)
            loss = (sent - recv) / sent * 100 if sent else 0.0
            data["packet_loss"] = loss
            losses.append(loss)
            lat = data.get("latency_ms") or data.get("latency_s") or 0.0
            lats.append(lat)
        self.flow_stats[switch_id] = stats

        if losses:
            self.loss_samples.append(statistics.mean(losses))
        if lats:
            self.latency_samples.append(statistics.mean(lats))
        return stats

    def collect_all(self, switch_ids):
        """
        Poll all switches and update metrics.
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
        Continuously collect for duration seconds.
        """
        end = time.time() + duration
        while time.time() < end:
            self.collect_all(switch_ids)
            time.sleep(self.interval)

    # Derived metrics
    def compute_aql(self, switch_id):
        """Average Queue Length for a switch."""
        hist = self.queue_history.get(switch_id, [])
        return statistics.mean(hist) if hist else None

    def compute_al(self):
        """Average Latency across all flows."""
        return statistics.mean(self.latency_samples) if self.latency_samples else None

    def compute_plr(self):
        """Packet Loss Rate (%) across samples."""
        return statistics.mean(self.loss_samples) if self.loss_samples else None

    def compute_cu(self, switch_id):
        """Average Channel Utilization (%) for a switch."""
        hist = self.util_history.get(switch_id, [])
        return statistics.mean(hist) if hist else None


# Example usage with dummy adapter
if __name__ == "__main__":

    class DummyAdapter:
        def get_queue_stats(self, sw):
            return {0: 5, 1: 10}

        def get_port_stats(self, sw):
            return {1: {"tx_bytes": 1e6}, 2: {"tx_bytes": 2e6}}

        def get_flow_stats(self, sw):
            return {
                "f1": {"packets_sent": 100, "packets_received": 90, "latency_ms": 20},
                "f2": {"packets_sent": 200, "packets_received": 195, "latency_ms": 15},
            }

    odl = DummyAdapter()
    tc = TelemetryCollector(odl, None, sample_interval=0.2)
    # Single poll
    tc.collect_all(["s1", "s2"])
    print("AQL s1:", tc.compute_aql("s1"))
    print("AL:", tc.compute_al())
    print("PLR:", tc.compute_plr())
    print("CU s2:", tc.compute_cu("s2"))
