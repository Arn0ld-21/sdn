# qos_classifier.py: модуль для класифікації потоків за QoS-класами

"""
qos_classifier.py: визначення QoS-класів і ваг для потоків трафіку.
"""

import random


class QoSClassifier:
    """
    Присвоює кожному потоку клас обслуговування (High, Medium, Low)
    та повертає відповідні ваги w_Q, w_W, w_R.
    """

    def __init__(self):
        # Типові ваги для трьох класів: [w_Q, w_W, w_R]
        self.class_weights = {
            "high": {"w_Q": 0.2, "w_W": 0.6, "w_R": 0.2},  # пріоритет затримки
            "medium": {"w_Q": 0.4, "w_W": 0.4, "w_R": 0.2},  # збалансований
            "low": {"w_Q": 0.6, "w_W": 0.2, "w_R": 0.2},  # пріоритет черги/надiйнiсть
        }

    def classify(self, pkt):
        """
        Визначає клас потоку. Можна перевизначити логику.
        За замовчуванням розподіляє рівномірно випадково.
        """
        return random.choice(["high", "medium", "low"])

    def get_weights(self, pkt):
        """
        Повертає ваги w_Q, w_W, w_R для заданого потоку pkt.
        """
        qos_class = self.classify(pkt)
        return self.class_weights[qos_class]


# Тестова перевірка
if __name__ == "__main__":
    qc = QoSClassifier()
    for i in range(5):
        pkt = {"id": f"flow{i}"}
        weights = qc.get_weights(pkt)
        print(f"Packet {pkt['id']} classified as {weights}")
