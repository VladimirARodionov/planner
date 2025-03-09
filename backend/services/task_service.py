from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Task, DurationSetting, TaskTypeSetting, StatusSetting, PrioritySetting
from backend.services.auth_service import AuthService

class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_service = AuthService(session)

    async def get_tasks(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Получить список задач пользователя с фильтрами"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return []

        query = select(Task).where(Task.user_id == user.telegram_id)

        if filters:
            if filters.get('status_id'):
                query = query.where(Task.status_id == filters['status_id'])
            if filters.get('priority_id'):
                query = query.where(Task.priority_id == filters['priority_id'])
            if filters.get('duration_id'):
                query = query.where(Task.duration_id == filters['duration_id'])
            if filters.get('type_id'):
                query = query.where(Task.type_id == filters['type_id'])

        query = query.options(
            selectinload(Task.status),
            selectinload(Task.priority),
            selectinload(Task.duration),
            selectinload(Task.type)
        )

        result = await self.session.execute(query)
        tasks = result.scalars().all()

        return [self._task_to_dict(task) for task in tasks]

    async def create_task(
        self,
        user_id: str,
        task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Создать новую задачу"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None
            
        # Проверяем наличие обязательного поля title
        if 'title' not in task_data:
            task_data['title'] = "Новая задача"  # Устанавливаем значение по умолчанию только если поле отсутствует
        elif not task_data['title']:  # Если поле есть, но пустое
            task_data['title'] = "Новая задача"

        # Проверяем, принадлежит ли тип задачи пользователю
        if task_data.get('type_id'):
            type_query = select(TaskTypeSetting).where(
                TaskTypeSetting.id == task_data['type_id'],
                TaskTypeSetting.user_id == user.telegram_id
            )
            type_result = await self.session.execute(type_query)
            if not type_result.scalar_one_or_none():
                return None

        # Получаем настройки по умолчанию, если они не указаны
        if not task_data.get('status_id'):
            status_query = select(StatusSetting).where(
                StatusSetting.user_id == user.telegram_id,
                StatusSetting.is_default == True
            )
            status_result = await self.session.execute(status_query)
            status = status_result.scalar_one_or_none()
            if status:
                task_data['status_id'] = status.id
                
        if not task_data.get('priority_id'):
            priority_query = select(PrioritySetting).where(
                PrioritySetting.user_id == user.telegram_id,
                PrioritySetting.is_default == True
            )
            priority_result = await self.session.execute(priority_query)
            priority = priority_result.scalar_one_or_none()
            if priority:
                task_data['priority_id'] = priority.id
                
        if not task_data.get('type_id'):
            type_query = select(TaskTypeSetting).where(
                TaskTypeSetting.user_id == user.telegram_id,
                TaskTypeSetting.is_default == True
            )
            type_result = await self.session.execute(type_query)
            task_type = type_result.scalar_one_or_none()
            if task_type:
                task_data['type_id'] = task_type.id

        task = Task(
            user_id=user.telegram_id,
            title=task_data['title'],
            description=task_data.get('description'),
            type_id=task_data.get('type_id'),
            status_id=task_data.get('status_id'),
            priority_id=task_data.get('priority_id'),
            duration_id=task_data.get('duration_id')
        )

        if task.duration_id:
            duration = await self.session.get(DurationSetting, task.duration_id)
            if duration:
                task.deadline = await duration.calculate_deadline_async(self.session)

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        return self._task_to_dict(task)

    async def update_task(
        self,
        user_id: str,
        task_id: int,
        task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Обновить задачу"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user.telegram_id:
            return None

        # Проверяем, принадлежит ли тип задачи пользователю
        if task_data.get('type_id'):
            type_query = select(TaskTypeSetting).where(
                TaskTypeSetting.id == task_data['type_id'],
                TaskTypeSetting.user_id == user.telegram_id
            )
            type_result = await self.session.execute(type_query)
            if not type_result.scalar_one_or_none():
                return None

        if 'title' in task_data:
            task.title = task_data['title']
        if 'description' in task_data:
            task.description = task_data['description']
        if 'type_id' in task_data:
            task.type_id = task_data['type_id']
        if 'status_id' in task_data:
            task.status_id = task_data['status_id']
        if 'priority_id' in task_data:
            task.priority_id = task_data['priority_id']
        if 'duration_id' in task_data:
            task.duration_id = task_data['duration_id']
            duration = await self.session.get(DurationSetting, task.duration_id)
            if duration:
                task.deadline = await duration.calculate_deadline_async(self.session)

        await self.session.commit()
        await self.session.refresh(task)

        return self._task_to_dict(task)

    async def delete_task(self, user_id: str, task_id: int) -> bool:
        """Удалить задачу"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return False

        task = await self.session.get(Task, task_id)
        if not task or task.user_id != user.telegram_id:
            return False

        await self.session.delete(task)
        await self.session.commit()

        return True

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Преобразовать задачу в словарь"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': {
                'id': task.type.id,
                'name': task.type.name,
                'color': task.type.color
            } if task.type else None,
            'status': {
                'id': task.status.id,
                'name': task.status.name,
                'color': task.status.color
            } if task.status else None,
            'priority': {
                'id': task.priority.id,
                'name': task.priority.name,
                'color': task.priority.color
            } if task.priority else None,
            'duration': {
                'id': task.duration.id,
                'name': task.duration.name,
                'type': task.duration.duration_type.value,
                'value': task.duration.value
            } if task.duration else None,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'is_overdue': task.is_overdue()
        } 