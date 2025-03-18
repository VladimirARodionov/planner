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
        
    async def set_user_bot_update_flag(self, user_id: str, needs_update: bool) -> bool:
        """Установить флаг необходимости обновления команд бота для пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            needs_update: True, если необходимо обновить команды бота, иначе False
            
        Returns:
            True, если флаг успешно установлен, иначе False
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
            
        stmt = update(User).where(User.telegram_id == user_id).values(needs_bot_update=needs_update)
        await self.session.execute(stmt)
        await self.session.commit()
        logger.debug(f"Установлен флаг needs_bot_update={needs_update} для пользователя {user_id}")
        return True
        
    async def get_users_needing_bot_update(self) -> list:
        """Получить список пользователей, которым необходимо обновить команды бота
        
        Returns:
            Список пользователей с флагом needs_bot_update=True
        """
        result = await self.session.execute(
            select(User).where(User.needs_bot_update == True)
        )
        return result.scalars().all() 