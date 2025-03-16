from typing import Any, Awaitable, Callable, Dict
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, CallbackQuery, Message
from fluentogram import TranslatorHub

from backend.database import get_session
from backend.services.auth_service import AuthService  # Предполагаю наличие такого сервиса

logger = logging.getLogger(__name__)

class TranslatorRunnerMiddleware(BaseMiddleware):
    def __init__(
            self,
            hub: TranslatorHub,
            default_lang: str = 'ru',
    ):
        super().__init__()
        self.hub = hub
        self.default_lang = default_lang

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Получаем ID пользователя из разных типов событий
        user_id = None

        # Получаем объект пользователя из event или из data
        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif "event_from_user" in data and isinstance(data["event_from_user"], User):
            user_id = data["event_from_user"].id
        elif "from_user" in data and isinstance(data["from_user"], User):
            user_id = data["from_user"].id

        # Установка языка по умолчанию
        locale = self.default_lang

        # Если нашли пользователя, пробуем получить его язык из базы
        if user_id:
            try:
                async with get_session() as session:
                    auth_service = AuthService(session)
                    user_language = await auth_service.get_user_language(str(user_id))

                    # Если язык найден и поддерживается, используем его
                    if user_language and user_language in ["ru", "en"]:
                        locale = user_language
                        logger.debug(f"Установлен язык из БД для пользователя {user_id}: {locale}")
            except Exception as e:
                logger.error(f"Ошибка при получении языка пользователя из БД: {e}")

                # Если не удалось получить язык из БД, используем язык из Telegram
                user = data.get("event_from_user") or data.get("from_user")
                if user and hasattr(user, "language_code") and user.language_code:
                    user_locale = user.language_code.split("-")[0]  # Отделяем базовый код (ru-RU -> ru)
                    if user_locale in ["ru", "en"]:
                        locale = user_locale
                        logger.debug(f"Установлен язык из Telegram для пользователя {user_id}: {locale}")

        # Устанавливаем переводчик в middleware_data
        data['i18n'] = self.hub.get_translator_by_locale(locale=locale)

        return await handler(event, data)
