import os
import multiprocessing

# Основные настройки Gunicorn
bind = "0.0.0.0:5000"
worker_class = "sync"  # Используем sync worker для работы с нашим async_route декоратором
workers = 2 #multiprocessing.cpu_count() * 2 + 1  # Рекомендуемое количество воркеров
threads = 1  # Количество потоков на воркера
max_requests = 1000  # Максимальное количество запросов до перезапуска воркера
max_requests_jitter = 50  # Добавляем случайность для предотвращения одновременного перезапуска всех воркеров
timeout = 120  # Таймаут для воркеров, увеличен для длительных операций
graceful_timeout = 30  # Время ожидания перед принудительным завершением воркера
keepalive = 65  # Для поддержания соединений с клиентами

# Настройки логирования
errorlog = "-"  # Вывод ошибок в stderr
accesslog = "-"  # Вывод логов доступа в stdout
loglevel = "info"  # Уровень логирования

# Настройка для передачи ID воркера в переменные окружения
def post_fork(server, worker):
    """Установка номера воркера в переменную окружения для бота"""
    worker_id = worker.age % server.num_workers  # Получаем уникальный ID воркера
    os.environ["GUNICORN_WORKER_ID"] = str(worker_id)
    
    # Устанавливаем случайный seed для каждого воркера
    import random
    import time
    random.seed(int(time.time()) + worker_id)

# Обработчик инициализации воркера
def worker_int(worker):
    """Обработчик сигнала SIGINT для воркера"""
    import logging
    logging.info(f"Воркер {worker.pid} остановлен")

# Обработчик запуска воркера
def on_starting(server):
    """Вызывается при запуске мастер-процесса"""
    import logging
    logging.info("Запуск Gunicorn сервера")

# Обработчик запуска воркера
def when_ready(server):
    """Вызывается, когда сервер готов к приему соединений"""
    import logging
    logging.info(f"Сервер готов к обработке запросов с {server.num_workers} воркерами") 