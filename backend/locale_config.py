from fluent.runtime import FluentLocalization, FluentResourceLoader
import logging
from typing import Dict
import inspect
import contextvars


from backend.database import get_session
from backend.services.auth_service import AuthService

logger = logging.getLogger(__name__)

loader = FluentResourceLoader("backend/locale_files/{locale}")

# Значение по умолчанию для локализации
default_i18n = FluentLocalization(["ru"], ["main.ftl"], loader)

# Словарь для кеширования локализаций по пользователям
user_locales: Dict[str, FluentLocalization] = {}

# Доступные языки
AVAILABLE_LANGUAGES = ["ru", "en"]

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
        # Пропускаем первые 3 фрейма (текущая функция, format_value, и вызов из обработчика)
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

def get_locale(language: str) -> FluentLocalization:
    """
    Получить локализацию для указанного языка
    
    Args:
        language: Код языка (ru/en)
        
    Returns:
        FluentLocalization для указанного языка
    """
    if language not in AVAILABLE_LANGUAGES:
        return default_i18n
    
    try:
        return FluentLocalization([language], ["main.ftl"], loader)
    except Exception as e:
        logger.error(f"Ошибка при создании локализации для языка {language}: {e}")
        return default_i18n

async def get_user_locale(user_id: str) -> FluentLocalization:
    """
    Получить локализацию для конкретного пользователя
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        FluentLocalization для пользователя или по умолчанию
    """
    # Всегда сначала проверяем язык в базе данных для обеспечения актуальности
    try:
        async with get_session() as session:
            auth_service = AuthService(session)
            language_code = await auth_service.get_user_language(user_id)
            
            # Если язык в базе данных отличается от кэша, обновляем кэш
            if language_code and language_code in AVAILABLE_LANGUAGES:
                need_update = True
                
                if user_id in user_locales:
                    # Проверяем, совпадает ли язык в кэше с языком в базе
                    cached_lang = user_locales[user_id].locales[0] if user_locales[user_id].locales else "ru"
                    need_update = cached_lang != language_code
                    logger.debug(f"Язык в кэше: {cached_lang}, язык в БД: {language_code}, требуется обновление: {need_update}")
                
                # Если языки не совпадают, обновляем кэш
                if need_update:
                    user_locales[user_id] = FluentLocalization([language_code], ["main.ftl"], loader)
                    logger.debug(f"Обновлен язык {language_code} из БД для пользователя {user_id}")
                
                # Устанавливаем пользователя в контекст
                if current_user_id.get() is None:
                    set_current_user_id(user_id)
                    
                return user_locales[user_id]
    except Exception as e:
        logger.exception(f"Ошибка при загрузке языка пользователя {user_id}: {e}")
    
    # Проверяем, есть ли локализация для пользователя в кеше
    if user_id in user_locales:
        # Устанавливаем текущего пользователя в контекстную переменную
        # только если она еще не установлена
        if current_user_id.get() is None:
            set_current_user_id(user_id)
            
        logger.debug(f"Используем язык из кэша для пользователя {user_id}: {user_locales[user_id].locales}")
        return user_locales[user_id]
                
    # Устанавливаем пользователя в контекст даже при использовании локализации по умолчанию
    if current_user_id.get() is None:
        set_current_user_id(user_id)
    
    logger.debug(f"Используем язык по умолчанию для пользователя {user_id}")    
    return default_i18n

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
        # Создаем новый экземпляр локализации для пользователя
        user_locales[user_id] = FluentLocalization([language], ["main.ftl"], loader)
        logger.debug(f"Установлен язык {language} для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при установке языка для пользователя {user_id}: {e}")
        return False

def set_user_locale_cache(user_id: str, locale: FluentLocalization) -> None:
    """
    Установить локализацию для пользователя напрямую в кеш
    
    Args:
        user_id: ID пользователя в Telegram
        locale: Объект локализации
    """
    user_locales[user_id] = locale

async def load_user_locale_from_db(user_id: str, auth_service) -> FluentLocalization:
    """
    Загрузить локализацию пользователя из базы данных
    
    Args:
        user_id: ID пользователя в Telegram
        auth_service: Экземпляр AuthService для работы с базой данных
        
    Returns:
        FluentLocalization для пользователя
    """
    # Если локализация уже есть в кеше, возвращаем ее
    if user_id in user_locales:
        return user_locales[user_id]
    
    # Иначе получаем язык из базы данных
    try:
        language = await auth_service.get_user_language(user_id)
        if language in AVAILABLE_LANGUAGES:
            user_locales[user_id] = FluentLocalization([language], ["main.ftl"], loader)
            return user_locales[user_id]
    except Exception as e:
        logger.error(f"Ошибка при загрузке языка пользователя {user_id} из БД: {e}")
    
    # В случае ошибки или отсутствия языка, возвращаем локализацию по умолчанию
    return default_i18n

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

async def reload_user_locale(user_id: str) -> bool:
    """
    Принудительно перезагружает локализацию пользователя из БД и обновляет кеш
    
    Args:
        user_id: ID пользователя в Telegram
        
    Returns:
        True если перезагрузка успешна, иначе False
    """
    try:
        async with get_session() as session:
            auth_service = AuthService(session)
            language_code = await auth_service.get_user_language(user_id)

            if language_code and language_code in AVAILABLE_LANGUAGES:
                language = language_code
                user_locales[user_id] = FluentLocalization([language], ["main.ftl"], loader)
                logger.debug(f"Перезагружен язык {language} из БД для пользователя {user_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при перезагрузке языка пользователя {user_id}: {e}")
        return False

# Создаем прокси для i18n, который будет автоматически использовать локализацию пользователя
class I18nProxy:
    @classmethod
    def format_value(cls, tag_id, args=None):
        # Сначала пытаемся получить пользователя из контекстной переменной
        user_id = current_user_id.get()
        if user_id:
            logger.debug(f"[I18nProxy] Используем локализацию для пользователя из контекста: {user_id}")
        
        # Если не нашли, пытаемся извлечь ID пользователя из стека вызовов
        if not user_id:
            user_id = get_current_user_id_from_stack()
            if user_id:
                # Сохраняем найденного пользователя в контекст для будущих запросов
                set_current_user_id(user_id)
                logger.debug(f"[I18nProxy] Используем локализацию для пользователя из стека: {user_id}")
        
        # Проверяем кеш локализаций
        if user_id and user_id in user_locales:
            logger.debug(f"[I18nProxy] Локализация: {user_locales[user_id].locales}")
            return user_locales[user_id].format_value(tag_id, args)
        
        # Если не нашли пользователя или его нет в кеше, используем локализацию по умолчанию
        if not user_id:
            logger.debug(f"[I18nProxy] Не удалось определить пользователя, используем локализацию по умолчанию для ключа: {tag_id}")
        elif user_id not in user_locales:
            logger.debug(f"[I18nProxy] Для пользователя {user_id} нет локализации в кеше, используем локализацию по умолчанию для ключа: {tag_id}")
            
        return default_i18n.format_value(tag_id, args)

# Создаем глобальный объект i18n, который будет использоваться во всем приложении
i18n = I18nProxy()
