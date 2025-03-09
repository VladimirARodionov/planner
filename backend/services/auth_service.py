from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.db.models import User

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        logger = logging.getLogger(__name__)
        
        logger.info(f"Поиск пользователя с ID {user_id}")
        
        result = await self.session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            logger.info(f"Пользователь с ID {user_id} найден")
        else:
            logger.info(f"Пользователь с ID {user_id} не найден")
        
        return user

    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
        """Создать нового пользователя"""
        logger = logging.getLogger(__name__)
        
        logger.info(f"Создание нового пользователя с telegram_id={telegram_id}, username={username}")
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        
        try:
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"Пользователь с telegram_id={telegram_id} успешно создан")
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя с telegram_id={telegram_id}: {e}")
            await self.session.rollback()
            raise
        
        return user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Аутентифицировать пользователя"""
        # TODO: Реализовать проверку пароля
        result = await self.session.execute(
            select(User).where(User.telegram_id == username)
        )
        return result.scalar_one_or_none() 