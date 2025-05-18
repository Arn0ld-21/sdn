import random
import time
import argparse
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info


class TrafficSimulator:
    """
    TrafficSimulator створює топологію Mininet та генерує UDP-потоки через iperf.
    """

    def __init__(self, num_switches=6, num_hosts=4, bandwidth="5M", duration=30):
        self.num_switches = num_switches
        self.num_hosts = num_hosts
        self.bandwidth = bandwidth
        self.duration = duration
        self.net = None
        self.hosts = []

    def build_topology(self):
        info("*** Building network topology\n")
        self.net = Mininet(
            controller=RemoteController, switch=OVSKernelSwitch, link=TCLink
        )
        # Контролер
        self.net.addController("c0", ip="127.0.0.1", port=6633)

        # Spine
        spine1 = self.net.addSwitch("s1")
        spine2 = self.net.addSwitch("s2")
        self.net.addLink(spine1, spine2, bw=100)

        # Leaf
        leafs = []
        for idx, name in enumerate(
            [f"s{i}" for i in range(3, self.num_switches + 1)], start=3
        ):
            leaf = self.net.addSwitch(name)
            self.net.addLink(leaf, spine1, bw=100)
            self.net.addLink(leaf, spine2, bw=100)
            leafs.append(leaf)

        # Hosts
        for idx, leaf in enumerate(leafs, start=1):
            h = self.net.addHost(f"h{idx}")
            self.net.addLink(h, leaf, bw=100)
            self.hosts.append(h)

        self.net.start()

    def start_iperf_servers(self):
        info("*** Starting iperf UDP servers on hosts\n")
        for h in self.hosts:
            h.cmd("iperf -s -u -p 5001 &")

    def start_iperf_clients(self, num_flows):
        info(f"*** Launching {num_flows} iperf UDP clients for {self.duration}s\n")
        for i in range(num_flows):
            src = random.choice(self.hosts)
            dst = random.choice([h for h in self.hosts if h != src])
            cmd = (
                f"iperf -c {dst.IP()} -u -p 5001 "
                f"-b {self.bandwidth} -t {self.duration} &"
            )
            info(f"{src.name} -> {dst.name}: {cmd}\n")
            src.cmd(cmd)

    def run(self, num_flows):
        self.build_topology()
        self.start_iperf_servers()
        time.sleep(1)
        self.start_iperf_clients(num_flows)
        time.sleep(self.duration + 1)
        self.net.stop()
        info("*** Traffic simulation complete\n")


if __name__ == "__main__":
    setLogLevel("info")
    parser = argparse.ArgumentParser(description="Mininet Traffic Simulator for QLLB")
    parser.add_argument(
        "--switches",
        type=int,
        default=6,
        help="Total number of switches (including 2 spine)",
    )
    parser.add_argument(
        "--hosts", type=int, default=4, help="Number of hosts (leaf switches)"
    )
    parser.add_argument(
        "--flows", type=int, default=10, help="Number of parallel iperf flows"
    )
    parser.add_argument(
        "--duration", type=int, default=30, help="Duration of each flow in seconds"
    )
    parser.add_argument(
        "--bandwidth", type=str, default="5M", help="Bandwidth per flow (e.g., 5M)"
    )
    args = parser.parse_args()

    sim = TrafficSimulator(
        num_switches=args.switches,
        num_hosts=args.hosts,
        bandwidth=args.bandwidth,
        duration=args.duration,
    )
    sim.run(num_flows=args.flows)
