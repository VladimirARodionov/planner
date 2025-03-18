from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    """Модель пользователя"""
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = "ru"  # Язык пользователя по умолчанию - русский 