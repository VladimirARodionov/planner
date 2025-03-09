from typing import Optional
from pydantic import BaseModel
from enum import Enum

class DurationType(str, Enum):
    """Типы продолжительности"""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"

class Duration(BaseModel):
    """Модель продолжительности задачи"""
    id: int
    name: str
    type: DurationType
    value: int
    is_default: bool
    is_active: bool 