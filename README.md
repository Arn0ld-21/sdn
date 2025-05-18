## Модуль: qllb_controller.py
### Призначення: 
реалізує «мозок» системи — контролер, який на основі зібраної телеметрії й політик QoS приймає рішення, куди направити кожен пакет, та забезпечує затримку на встановлення нових правил (FlowMod).

```
from qos_classifier_ApplicationPlane import QoSClassifier
from telemetry_collector_ContrrolPlane import TelemetryCollector
```
- QoSClassifier (Application Plane) — видає ваги для трьох критеріїв (черга, латенс, надійність) залежно від типу потоку (VoIP, відео, дані).

- TelemetryCollector (Control Plane) — збирає телеметрію (довжини черг, затримки, втрати, завантаження) із комутаторів.


```
def __init__(self, env, leaves, spines, telemetry_collector,
    qmax=100, flowmod_delay=0.0, qos_classifier=None):
    self.env = env
    self.leaves = leaves
    self.spines = spines
    self.tc = telemetry_collector
    self.qmax = qmax
    self.flowmod_delay = flowmod_delay
    self.qc = qos_classifier if qos_classifier else QoSClassifier()
    self.metrics = []
```

- env — об’єкт SimPy, потрібен для таймаутів і корутин.
- leaves / spines — списки емуляторних або реальних (Mininet) комутаторів.
- telemetry_collector — інстанс TelemetryCollector, через який контролер отримує актуальні метрики.
- qmax — максимальний розмір черги, використовується для нормалізації.
- flowmod_delay — додаткова затримка (у секундах) на інсталяцію правил перед передачею пакета.
- qc — екземпляр QoSClassifier, або ваш власний, який задається через аргумент.
- metrics — список усіх відліків латенсу пакетів для подальшої аналітики.

### Метод `select_route`

Збір телеметрії: викликає collect_queue_stats, щоб оновити значення queue_stats.
- Отримання ваг: get_weights(pkt) повертає відносні ваги для критеріїв згідно з політикою QoS.
- Оцінка кожного спайн-лінку: розрахунок цільової функції 𝑈 як зважена сума:
- Повернення номера порту (індекс спайн-лінка із найвищим 𝑈).

### Метод `dispatch`

Визначає leaf-комутатор за полем pkt["src"].leaf.

- Вибір маршруту — викликає select_route.
- FlowMod затримка — імітація часу на встановлення правил у контролері.
- Передача пакета — виклик leaf.put(pkt, spine).
- Збір латенсу — читає з pkt["sink"], розраховує та зберігає.
- Телеметрія — поповнення latency_samples.


### workflow
Хост генерує pkt і запускає controller.dispatch(pkt).

- dispatch → select_route → збір метрик черги → обчислення U → затримка FlowMod → передача.
- Link.serve() очищає чергу, кладе depart_time → пакет повертається в sink.
- dispatch добирає depart_time і рахує кінцеву латенсі, яку одразу записує й у контролера, й у TelemetryCollector.

Цей модуль є центральним елементом вашої системи SDN, що демонструє мультиоб’єктне управління: він одночасно оптимізує три метрики (чергу, латенс, надійність)



## Модуль: qos_classifier.py
### Призначення: призначає кожному потоку один із трьох QoS-класів (High, Medium, Low) і повертає відповідні ваги для трьох критеріїв оптимізації — довжини черги (w_Q), затримки (w_W) та надійності (w_R).

- High-priority (наприклад, VoIP): велику вагу даємо затримці, щоб мінімізувати W.
- Medium: рівномірний розподіл уваги на всі метрики.
- Low-priority: фокус на довжині черги (через w_Q) і надійності.

### Метод classify(pkt)

- За замовчуванням потік випадково отримує один із трьох класів з рівномірним розподілом.
- Можливе розширення: замість випадкового вибору тут можна аналізувати атрибути pkt (наприклад, pkt['class'] або порт, з якого прийшов) та віддавати конкретний клас.


### Метод get_weights(pkt)

- Спочатку визначаємо qos_class через classify().
- Повертаємо словник із трьома вагами, який потім використовується в QLLBController при обчисленні цільової функції UUU.


### Як модуль інтегрується в систему
- QLLBController викликає weights = qc.get_weights(pkt).
- Після цього з отриманих w_Q, w_W, w_R контролер формує
U=wQ(1−QQmax⁡)+wW(1W)+wR R U = w_Q\Bigl(1 - \frac{Q}{Q_{\max}}\Bigr) + w_W\Bigl(\frac1W\Bigr) + w_R\,RU=wQ(1−QmaxQ)+wW(W1)+wRR 
— таким чином пріоритет потоку (через class_weights) прямо впливає на вибір маршруту.


## Модуль: telemetry_collector.py
### Призначення: централізовано збирати й обробляти телеметрію з мережевих комутаторів (черги, порти, потоки), накопичувати історії, обчислювати похідні метрики (AQL, AL, PLR, CU) та надавати ці дані контролеру й аналітиці.


```
self.queue_stats   = {}                      # поточні довжини черг {sw: {queue_id: length}}
self.port_stats    = {}                      # поточна статистика портів {sw: {port: {...}}}
self.flow_stats    = {}                      # поточна статистика потоків {sw: {flow_id: {...}}}
self.queue_history = defaultdict(list)       # історія середніх черг за кожен цикл опитування
self.util_history  = defaultdict(list)       # історія середніх завантажень каналів
self.latency_samples = []                    # вибірки затримок потоків
self.loss_samples    = []                    # вибірки рівнів втрат
```

- odl / onos — адаптери для опитування через OpenDaylight та ONOS.
- interval — період опитування (за замовчуванням 0.1 с).

### Збір кожного типу статистики

#### collect_queue_stats(switch_id)
```
stats = self.odl.get_queue_stats(switch_id)
self.queue_stats[switch_id] = stats
avg_q = mean(stats.values())
self.queue_history[switch_id].append(avg_q)
```

- Опитує адаптер, отримує довжини всіх черг на комутаторі.
- Зберігає у queue_stats.
- Обчислює середню довжину (avg_q) і додає до історії queue_history[switch_id].

#### collect_port_stats(switch_id)
```
stats = self.odl.get_port_stats(switch_id)
# додаємо data["utilization"] = (tx_bytes*8)/(interval*1e8)*100
self.port_stats[switch_id] = stats
avg_util = mean(utilizations)
self.util_history[switch_id].append(avg_util)
```

- Опитує байти, що передані за період, переводить у відсоток використання смуги (CU).
- Зберігає у port_stats.
- Додає середню завантаженість у util_history.

#### collect_flow_stats(switch_id)
```
stats = self.odl.get_flow_stats(switch_id)
# для кожного flow: обчислює loss = (sent−recv)/sent*100, latency
self.flow_stats[switch_id] = stats
self.loss_samples.append(mean(losses))
self.latency_samples.append(mean(lats))
```

- Опитує статистику потоків: кількість надісланих і отриманих пакетів, затримки.
- Обчислює Packet Loss Rate (PLR) і Latency для кожного потоку, потім зберігає середні значення у loss_samples та latency_samples.

### Обчислення похідних метрик
```
compute_aql(sw) → mean(self.queue_history[sw])
compute_al()    → mean(self.latency_samples)
compute_plr()   → mean(self.loss_samples)
compute_cu(sw)  → mean(self.util_history[sw])
```
- AQL (Average Queue Length) — середня довжина черги за весь експеримент.
- AL (Average Latency) — середня затримка всіх потоків.
- PLR (Packet Loss Rate) — середня втратність пакетів, %.
- CU (Channel Utilization) — середня завантаженість каналів, %.


