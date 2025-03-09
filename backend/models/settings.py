from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.models.status import Status
from backend.models.priority import Priority
from backend.models.duration import Duration
from backend.models.task_type import TaskType

class Settings(BaseModel):
    """Модель настроек пользователя"""
    statuses: List[Status] = []
    priorities: List[Priority] = []
    durations: List[Duration] = []
    task_types: List[TaskType] = [] 