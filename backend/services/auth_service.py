from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.db.models import User

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        logger.debug(f"Поиск пользователя с ID {user_id}")
        
        result = await self.session.execute(
            select(User).where(User.telegram_id == user_id)
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
            select(User).where(User.telegram_id == username)
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
            
        stmt = update(User).where(User.telegram_id == user_id).values(language=language)
        await self.session.execute(stmt)
        await self.session.commit()
        return True 