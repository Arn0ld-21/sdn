import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Спробуємо зчитати реальні дані; якщо нема, підставимо демонстраційні
try:
    df = pd.read_csv("results.csv")
    print("Loaded results.csv")
except FileNotFoundError:
    print("results.csv not found, using sample data")
    df = pd.DataFrame(
        {
            "flows": [2, 10, 20, 25],
            "avg_latency": [0.028, 0.052, 0.083, 0.105],
            "p95_latency": [0.057, 0.098, 0.145, 0.195],
        }
    )

# Верхня похибка = p95 - avg; нижня = 0 (щоб не йти в негатив)
errors = df["p95_latency"] - df["avg_latency"]
lower_errors = np.zeros_like(errors)
upper_errors = errors

# Малюємо
plt.figure(figsize=(8, 5))
x = np.arange(len(df))
plt.bar(
    x, df["avg_latency"], yerr=[lower_errors, upper_errors], capsize=5, color="#FFA500"
)
plt.xticks(x, df["flows"])
plt.xlabel("Кількість потоків")
plt.ylabel("Середня затримка (s)")
plt.title("Залежність середньої затримки від кількості потоків")

# Сітка по горизонталі й початок осі з нуля
plt.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.7)
plt.ylim(bottom=0)

plt.tight_layout()
plt.savefig("latency_plot_fixed.png")
plt.show()
