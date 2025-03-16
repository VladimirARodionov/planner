from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram_dialog import DialogManager
import logging
from typing import Dict, Any, Callable, Awaitable
from backend.locale_config import get_user_locale, set_current_user_id

logger = logging.getLogger(__name__)

class I18nMiddleware(BaseMiddleware):
    """Middleware для установки языка пользователя в контекст запроса"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Определяем ID пользователя
        user_id = None
        
        # Проверяем тип события и извлекаем ID пользователя
        if isinstance(event, Message) and event.from_user:
            user_id = str(event.from_user.id)
            logger.debug(f"Получен ID пользователя из сообщения: {user_id}")
        
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = str(event.from_user.id)
            logger.debug(f"Получен ID пользователя из callback_query: {user_id}")
        
        # Проверяем наличие dialog_manager для aiogram-dialog
        elif 'dialog_manager' in data:
            dialog_manager = data['dialog_manager']
            if isinstance(dialog_manager, DialogManager) and dialog_manager.event.from_user:
                user_id = str(dialog_manager.event.from_user.id)
                logger.debug(f"Получен ID пользователя из dialog_manager: {user_id}")
        
        # Если нашли ID пользователя, устанавливаем его в контекст
        if user_id:
            # Устанавливаем ID пользователя в контекстную переменную
            set_current_user_id(user_id)
            
            # Загружаем язык пользователя
            locale = get_user_locale(user_id)
            logger.debug(f"Установлен язык {locale} для пользователя {user_id}")
        
        # Вызываем следующий обработчик
        return await handler(event, data) 