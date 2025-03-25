from datetime import datetime, UTC, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.db.models import User, AuthStates
from backend.load_env import env_config

logger = logging.getLogger(__name__)

# Время жизни состояния авторизации в секундах (10 минут)
AUTH_STATE_TTL = 600

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        logger.debug(f"Поиск пользователя с ID {user_id}")
        
        result = await self.session.execute(
            select(User).where(User.telegram_id == int(user_id))
        )
        user = result.scalar_one_or_none()
        
        if user:
            logger.debug(f"Пользователь с ID {user_id} найден")
        else:
            logger.debug(f"Пользователь с ID {user_id} не найден")
        
        return user

    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
        """Создать нового пользователя"""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Аутентифицировать пользователя"""
        # TODO: Реализовать проверку пароля
        result = await self.session.execute(
            select(User).where(User.telegram_id == int(username))
        )
        return result.scalar_one_or_none()

    async def get_user_language(self, user_id: str) -> str:
        """Получить предпочитаемый язык пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return 'ru'  # По умолчанию русский, если пользователь не найден
        return user.language

    async def set_user_language(self, user_id: str, language: str) -> bool:
        """Установить предпочитаемый язык пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
            
        stmt = update(User).where(User.telegram_id == int(user_id)).values(language=language)
        await self.session.execute(stmt)
        await self.session.commit()
        bot = Bot(token=env_config.get('TELEGRAM_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        from backend.locale_config import get_user_locale
        from backend.run import set_user_commands
        locale = await get_user_locale(user_id)
        await set_user_commands(bot, user_id, locale)
        return True

    # Функция для добавления состояния авторизации в базу данных
    async def add_auth_state(self, state:str, redirect_url:str):
        """Добавляет состояние авторизации в базу данных"""
        result = await self.session.execute(
            select(AuthStates).where(AuthStates.created_at < (datetime.now(UTC) - timedelta(seconds=AUTH_STATE_TTL)))) # type: ignore
        states = result.scalars().all()
        deleted = len(states)
        for st in states:
            await self.session.delete(st)
        if deleted:
            logger.info(f"Очищено {deleted} просроченных состояний авторизации")

        # Добавляем новое состояние
        auth_state = AuthStates(state=state, redirect_url=redirect_url)
        self.session.add(auth_state)
        await self.session.commit()
        logger.info(f"Состояние авторизации {state} сохранено в базе данных")
        return True

    # Функция для получения и удаления состояния авторизации из базы данных
    async def get_and_remove_auth_state(self, state:str):
        """Получает и удаляет состояние авторизации из базы данных"""
        result = await self.session.execute(
            select(AuthStates).where(AuthStates.state == state).where(AuthStates.created_at < (datetime.now(UTC) + timedelta(seconds=AUTH_STATE_TTL)))) # type: ignore
        row = result.scalar_one_or_none()
        if not row:
            logger.error(f"Состояние авторизации {state} не найдено в базе данных или истекло")
            return None

        redirect_url = row.redirect_url
        # Проверяем, не истекло ли состояние
        logger.info(f"Время создания состояния авторизации {state}: {row.created_at} ; now={datetime.now(UTC)}")
        # Удаляем состояние
        await self.session.delete(row)
        await self.session.commit()
        logger.info(f"Состояние авторизации {state} получено и удалено из базы данных")
        return redirect_url

    # Функция для очистки старых состояний авторизации
    async def cleanup_auth_states(self):
        """Очищает старые состояния авторизации из базы данных"""
        result = await self.session.execute(
            select(AuthStates).where(AuthStates.created_at < datetime.now(UTC) - timedelta(seconds=AUTH_STATE_TTL))) # type: ignore
        states = result.scalars().all()
        deleted = len(states)
        for state in states:
            await self.session.delete(state)
        await self.session.commit()

        if deleted:
            logger.info(f"Очищено {deleted} просроченных состояний авторизации")
