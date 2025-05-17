# orchestrator.py: інтеграція всіх модулів у єдиний інтерфейс запуску

#!/usr/bin/env python3
"""
Orchestrator запуску:
- SimPy-симуляція з TestSuite
- Mininet-симуляція з TrafficSimulator
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrator for QLLB system: simpy or mininet mode"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # SimPy mode
    parser_simpy = subparsers.add_parser("simpy", help="Run SimPy-based tests")
    parser_simpy.add_argument(
        "--flows_list",
        nargs="+",
        type=int,
        default=[2, 10, 20, 25],
        help="List of flow counts to test",
    )
    parser_simpy.add_argument(
        "--repeats", type=int, default=5, help="Number of repeats for averaging"
    )
    parser_simpy.add_argument(
        "--sim_time", type=int, default=100, help="Simulation time in seconds"
    )
    parser_simpy.add_argument(
        "--flow_rate", type=float, default=0.5, help="Flow generation rate (lambda)"
    )

    # Mininet mode
    parser_mn = subparsers.add_parser("mininet", help="Run Mininet-based traffic")
    parser_mn.add_argument(
        "--flows", type=int, default=10, help="Number of parallel iperf flows"
    )
    parser_mn.add_argument(
        "--duration", type=int, default=30, help="Duration of iperf flows in seconds"
    )
    parser_mn.add_argument(
        "--bandwidth", type=str, default="5M", help="Bandwidth per flow (e.g., 5M)"
    )
    parser_mn.add_argument(
        "--hosts", type=int, default=4, help="Number of hosts (leaf switches)"
    )

    args = parser.parse_args()

    if args.mode == "simpy":
        # Lazy import to avoid simpy dependency in Mininet mode
        from testsuite_ApplicationPlane import TestSuite

        ts = TestSuite(
            flows_list=args.flows_list,
            repeats=args.repeats,
            sim_time=args.sim_time,
            flow_rate=args.flow_rate,
        )
        print("Starting SimPy TestSuite...")
        ts.run()
        csv_name = "results_simpy.csv"
        ts.export_csv(csv_name)
        print(f"SimPy results saved to {csv_name}")

    elif args.mode == "mininet":
        from traffic_sim_DataPlane import TrafficSimulator

        print("Starting Mininet TrafficSimulator...")
        sim = TrafficSimulator(
            num_switches=args.hosts + 2,  # hosts + 2 spine
            num_hosts=args.hosts,
            bandwidth=args.bandwidth,
            duration=args.duration,
        )
        sim.run(num_flows=args.flows)
        print("Mininet simulation complete")

    else:
        print("Unknown mode. Choose 'simpy' or 'mininet'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
