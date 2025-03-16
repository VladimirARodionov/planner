import os

import i18n
import logging
from typing import Dict
import inspect
import contextvars

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка путей к файлам локализации
locale_dir_path = os.path.dirname(__file__) + '/locale_files/'
print(locale_dir_path)
i18n.load_path.append(locale_dir_path)
i18n.set('filename_format', '{locale}.json')
i18n.set('file_format', 'json')
i18n.set('enable_memoization', True)  # Кэширование для производительности
i18n.set('fallback', 'ru')  # Язык по умолчанию

# Доступные языки
AVAILABLE_LANGUAGES = ["ru", "en"]

# Словарь для кеширования локализаций по пользователям
user_languages: Dict[str, str] = {}

# Контекстная переменная для хранения ID текущего пользователя в запросе
current_user_id = contextvars.ContextVar('current_user_id', default=None)

def set_current_user_id(user_id: str) -> None:
    """
    Устанавливает ID текущего пользователя в контекстную переменную
    
    Args:
        user_id: ID пользователя в Telegram
    """
    current_user_id.set(user_id)
    logger.debug(f"Установлен текущий пользователь в контекст: {user_id}")

def get_current_user_id_from_stack():
    """
    Находит ID пользователя из стека вызовов, анализируя параметры функций
    """
    # Получаем стек вызовов
    stack = inspect.stack()
    
    try:
        # Пропускаем первые 3 фрейма (текущая функция, t, и вызов из обработчика)
        for frame_info in stack[2:]:
            frame = frame_info.frame
            # Извлекаем локальные переменные из фрейма
            local_vars = frame.f_locals
            
            # Ищем параметры, которые могут содержать ID пользователя
            # Проверяем объект message
            if 'message' in local_vars and hasattr(local_vars['message'], 'from_user') and local_vars['message'].from_user:
                logger.debug(f"Найден пользователь из message: {local_vars['message'].from_user.id}")
                return str(local_vars['message'].from_user.id)
            
            # Проверяем объект callback_query
            if 'callback_query' in local_vars and hasattr(local_vars['callback_query'], 'from_user') and local_vars['callback_query'].from_user:
                logger.debug(f"Найден пользователь из callback_query: {local_vars['callback_query'].from_user.id}")
                return str(local_vars['callback_query'].from_user.id)
            
            # Прямое указание user_id
            if 'user_id' in local_vars and local_vars['user_id'] is not None:
                logger.debug(f"Найден прямой user_id: {local_vars['user_id']}")
                return str(local_vars['user_id'])
            
            # Проверяем dialog_manager
            if 'dialog_manager' in local_vars and hasattr(local_vars['dialog_manager'], 'event'):
                event = local_vars['dialog_manager'].event
                if hasattr(event, 'from_user') and event.from_user:
                    logger.debug(f"Найден пользователь из dialog_manager: {event.from_user.id}")
                    return str(event.from_user.id)
                    
            # Проверка на aiogram обновление (update)
            if 'update' in local_vars:
                update = local_vars['update']
                if hasattr(update, 'message') and update.message and hasattr(update.message, 'from_user'):
                    logger.debug(f"Найден пользователь из update.message: {update.message.from_user.id}")
                    return str(update.message.from_user.id)
                if hasattr(update, 'callback_query') and update.callback_query and hasattr(update.callback_query, 'from_user'):
                    logger.debug(f"Найден пользователь из update.callback_query: {update.callback_query.from_user.id}")
                    return str(update.callback_query.from_user.id)
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя из стека: {e}")
    
    return None

def get_locale(language: str) -> str:
    """
    Получить локализацию для указанного языка
    
    Args:
        language: Код языка (ru/en)
        
    Returns:
        Код языка (ru/en)
    """
    if language not in AVAILABLE_LANGUAGES:
        return "ru"
    
    return language

def get_user_locale(user_id: str) -> str:
    """
    Получить локализацию для конкретного пользователя
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        Код языка (ru/en)
    """
    # Проверяем, есть ли локализация для пользователя в кеше
    if user_id in user_languages:
        # Устанавливаем текущего пользователя в контекстную переменную
        # только если она еще не установлена
        if current_user_id.get() is None:
            set_current_user_id(user_id)
            
        return user_languages[user_id]
    else:
        return "ru"

def set_user_locale(user_id: str, language: str) -> bool:
    """
    Установить язык для пользователя в кеше
    
    Args:
        user_id: ID пользователя в Telegram
        language: Код языка (ru/en)
        
    Returns:
        True, если язык успешно установлен, иначе False
    """
    if language not in AVAILABLE_LANGUAGES:
        logger.warning(f"Попытка установить неподдерживаемый язык: {language}")
        return False
    
    try:
        # Сохраняем язык пользователя в кеш
        user_languages[user_id] = language
        logger.debug(f"Установлен язык {language} для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке языка для пользователя {user_id}: {e}")
        return False

def set_user_locale_cache(user_id: str, locale: str) -> None:
    """
    Установить локализацию для пользователя напрямую в кеш
    
    Args:
        user_id: ID пользователя в Telegram
        locale: Код языка (ru/en)
    """
    user_languages[user_id] = locale

async def load_user_locale_from_db(user_id: str, auth_service) -> str:
    """
    Загрузить локализацию пользователя из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
        auth_service: Экземпляр AuthService для работы с базой данных
        
    Returns:
        Код языка (ru/en)
    """
    # Если локализация уже есть в кеше, возвращаем ее
    if user_id in user_languages:
        return user_languages[user_id]
    
    # Иначе получаем язык из базы данных
    try:
        language = await auth_service.get_user_language(user_id)
        if language in AVAILABLE_LANGUAGES:
            user_languages[user_id] = language
            return language
    except Exception as e:
        logger.error(f"Ошибка при загрузке языка пользователя {user_id} из БД: {e}")
    
    # В случае ошибки или отсутствия языка, возвращаем локализацию по умолчанию
    return "ru"

async def save_user_locale_to_db(user_id: str, language: str, auth_service) -> bool:
    """
    Сохранить выбранный язык пользователя в базе данных
    
    Args:
        user_id: ID пользователя в Telegram
        language: Код языка (ru/en)
        auth_service: Экземпляр AuthService для работы с базой данных
        
    Returns:
        True, если язык успешно сохранен, иначе False
    """
    if language not in AVAILABLE_LANGUAGES:
        logger.warning(f"Попытка сохранить неподдерживаемый язык: {language}")
        return False
    
    try:
        # Сначала обновляем кеш
        set_user_locale(user_id, language)
        
        # Затем сохраняем в базу данных
        return await auth_service.set_user_language(user_id, language)
    except Exception as e:
        logger.error(f"Ошибка при сохранении языка пользователя {user_id} в БД: {e}")
        return False

def t(key: str, **kwargs):
    """
    Получение локализованного текста для текущего пользователя
    
    Args:
        key: Ключ локализации
        kwargs: Параметры для подстановки в строку
        
    Returns:
        Локализованный текст
    """
    # Сначала пытаемся получить пользователя из контекстной переменной
    user_id = current_user_id.get()
    if user_id:
        logger.debug(f"[t] Используем локализацию для пользователя из контекста: {user_id}")
    
    # Если не нашли, пытаемся извлечь ID пользователя из стека вызовов
    if not user_id:
        user_id = get_current_user_id_from_stack()
        if user_id:
            # Сохраняем найденного пользователя в контекст для будущих запросов
            set_current_user_id(user_id)
            logger.debug(f"[t] Используем локализацию для пользователя из стека: {user_id}")
    
    # Определяем язык пользователя
    locale = "ru"  # Язык по умолчанию
    if user_id and user_id in user_languages:
        locale = user_languages[user_id]
    i18n.set('locale', locale)
    
    # Возвращаем локализованный текст
    try:
        return i18n.t(key, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка при получении локализации для ключа '{key}': {e}")
        # В случае ошибки возвращаем ключ
        return key
