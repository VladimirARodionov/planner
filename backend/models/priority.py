from typing import Optional
from pydantic import BaseModel

class Priority(BaseModel):
    """Модель приоритета задачи"""
    id: int
    name: str
    color: str
    order: int
    is_default: bool
    is_active: bool 