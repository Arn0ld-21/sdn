# testsuite.py: модуль для автоматизації запуску сценаріїв тестування та збору результатів у CSV

import csv
import statistics
from simulation_simpy_DataPlane import (
    run_simulation,
)  # Переконайтеся, що simulation_simpy.py у тій же папці


class TestSuite:
    """
    Автоматизує запуск run_simulation для різних конфігурацій потоків
    та збір ключових метрик (середня затримка і 95%-перцентиль).
    """

    def __init__(self, flows_list=None, repeats=5, sim_time=100, flow_rate=0.5):
        """
        flows_list: список кількостей потоків (наприклад [2,10,20,25])
        repeats: кількість повторних запусків для усереднення
        sim_time: тривалість симуляції в секундах
        flow_rate: інтенсивність генерації пакетів (λ)
        """
        self.flows_list = flows_list or [2, 10, 20, 25]
        self.repeats = repeats
        self.sim_time = sim_time
        self.flow_rate = flow_rate
        self.results = []

    def run(self):
        """
        Запускає серію симуляцій і збирає усереднені метрики.
        """
        for flows in self.flows_list:
            latencies = []
            p95s = []
            for _ in range(self.repeats):
                mean_lat, p95_lat = run_simulation(
                    num_flows=flows, flow_rate=self.flow_rate, sim_time=self.sim_time
                )
                latencies.append(mean_lat)
                p95s.append(p95_lat)
            # Усереднюємо результати
            avg_lat = statistics.mean(latencies)
            avg_p95 = statistics.mean(p95s)
            self.results.append(
                {
                    "flows": flows,
                    "avg_latency": round(avg_lat, 3),
                    "p95_latency": round(avg_p95, 3),
                }
            )

    def export_csv(self, filename="results.csv"):
        """
        Експортує зібрані результати у CSV-файл.
        """
        with open(filename, "w", newline="") as csvfile:
            fieldnames = ["flows", "avg_latency", "p95_latency"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.results:
                writer.writerow(row)
        print(f"Results exported to {filename}")


if __name__ == "__main__":
    # Приклад використання
    ts = TestSuite(repeats=3, sim_time=60, flow_rate=0.5)
    ts.run()
    ts.export_csv()
    print("Test suite completed!")
