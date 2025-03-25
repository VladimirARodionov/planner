from functools import wraps
import asyncio
import threading

# Глобальный словарь для хранения циклов событий по идентификаторам потоков
_thread_local = threading.local()


def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Получаем ID текущего потока
        thread_id = threading.get_ident()
        
        # Получаем или создаем цикл событий для текущего потока
        if not hasattr(_thread_local, 'loop') or _thread_local.loop is None or _thread_local.loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _thread_local.loop = loop
        
        # Используем существующий цикл событий
        loop = _thread_local.loop
        
        # Выполняем асинхронную функцию в этом цикле событий
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        except Exception as e:
            # Не закрываем цикл событий при ошибке, но пробрасываем исключение дальше
            raise e
            
        # Важно! Не закрываем цикл событий после выполнения
        # Цикл будет переиспользован для следующих запросов в этом потоке
    
    return wrapped
