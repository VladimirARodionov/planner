from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Аутентифицировать пользователя"""
        # TODO: Реализовать проверку пароля
        result = await self.session.execute(
            select(User).where(User.telegram_id == username)
        )
        return result.scalar_one_or_none() 