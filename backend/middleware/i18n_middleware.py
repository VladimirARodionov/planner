from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
import logging

from backend.locale_config import reload_user_locale, get_user_locale, set_current_user_id

logger = logging.getLogger(__name__)

class TranslatorRunnerMiddleware(BaseMiddleware):
    def __init__(
            self, 
            hub
    ):
        self.hub = hub

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Получаем ID пользователя из разных типов событий
        user_id = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            data["event_from_user"] = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            data["event_from_user"] = event.from_user
        else:
            # Пытаемся получить пользователя из данных
            user = data.get("event_from_user") or data.get("from_user")
            if user:
                user_id = user.id

        # Определяем язык по умолчанию
        locale = "ru"
        
        # Если получили ID пользователя, пробуем обновить локализацию из БД
        if user_id:
            try:
                # Устанавливаем текущего пользователя в контекст
                set_current_user_id(str(user_id))
                
                # Принудительно обновляем локализацию пользователя из БД
                # Это нужно чтобы исключить несоответствие между языком в БД и языком в кэше
                await reload_user_locale(str(user_id))
                
                # Получаем актуальную локализацию
                user_locale = await get_user_locale(str(user_id))
                if user_locale and hasattr(user_locale, 'locales') and user_locale.locales:
                    locale = user_locale.locales[0]
                    logger.debug(f"Обновлена локализация для пользователя {user_id}: {locale}")
            except Exception as e:
                logger.exception(f"Ошибка при обновлении локализации в middleware: {e}")
        
        # Добавляем локализацию в middleware данные
        data["i18n"] = self.hub.get_translator_by_locale(locale)
            
        # Вызываем следующий обработчик
        return await handler(event, data)
