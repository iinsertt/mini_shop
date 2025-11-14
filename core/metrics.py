from prometheus_client import Counter, Gauge, start_http_server
import threading

metric_errors_total = Counter(
    "bot_errors_total",
    "Количество ошибок, произошедших в боте"
)

purchases_total = Counter(
    "bot_purchases_total",
    "Общее количество покупок"
)

withdraw_requests_total = Counter(
    "bot_withdraw_requests_total",
    "Количество созданных заявок на вывод"
)

users_total = Gauge(
    "bot_users_total",
    "Количество зарегистрированных пользователей"
)

cards_total = Gauge(
    "bot_cards_total",
    "Количество карточек в системе"
)


def start_metrics_server(port: int = 9000):
    def run():
        start_http_server(port)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
