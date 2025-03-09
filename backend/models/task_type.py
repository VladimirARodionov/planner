from typing import Optional
from pydantic import BaseModel

class TaskType(BaseModel):
    """Модель типа задачи"""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    order: int
    is_default: bool
    is_active: bool 