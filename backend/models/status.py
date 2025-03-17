from pydantic import BaseModel

class Status(BaseModel):
    """Модель статуса задачи"""
    id: int
    name: str
    code: str
    color: str
    order: int
    is_default: bool
    is_final: bool
    is_active: bool 