from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging
import asyncio

from backend.db.models import Task, DurationSetting, TaskTypeSetting, StatusSetting, PrioritySetting
from backend.services.auth_service import AuthService

logger = logging.getLogger(__name__)

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

        # Используем asyncio.gather для параллельного выполнения
        return await asyncio.gather(*[self._task_to_dict(task) for task in tasks])

    async def create_task(
        self,
        user_id: str,
        task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Создать новую задачу"""
        logger.debug(f"Creating task for user {user_id} with data: {task_data}")

        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
            
        # Проверяем наличие обязательного поля title
        if 'title' not in task_data:
            task_data['title'] = "Новая задача"  # Устанавливаем значение по умолчанию только если поле отсутствует
            logger.debug("Title not provided, using default: 'Новая задача'")
        elif not task_data['title']:  # Если поле есть, но пустое
            task_data['title'] = "Новая задача"
            logger.debug("Title is empty, using default: 'Новая задача'")

        # Проверяем, принадлежит ли тип задачи пользователю
        if task_data.get('type_id'):
            logger.debug(f"Checking if type_id {task_data['type_id']} belongs to user {user_id}")
            type_query = select(TaskTypeSetting).where(
                TaskTypeSetting.id == task_data['type_id'],
                TaskTypeSetting.user_id == user.telegram_id
            )
            type_result = await self.session.execute(type_query)
            if not type_result.scalar_one_or_none():
                logger.error(f"Type {task_data['type_id']} does not belong to user {user_id}")
                return None
            logger.debug(f"Type {task_data['type_id']} belongs to user {user_id}")

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
                logger.debug(f"Using default status with ID: {status.id}")
            else:
                logger.debug("No default status found")
                
        if not task_data.get('priority_id'):
            priority_query = select(PrioritySetting).where(
                PrioritySetting.user_id == user.telegram_id,
                PrioritySetting.is_default == True
            )
            priority_result = await self.session.execute(priority_query)
            priority = priority_result.scalar_one_or_none()
            if priority:
                task_data['priority_id'] = priority.id
                logger.debug(f"Using default priority with ID: {priority.id}")
            else:
                logger.debug("No default priority found")
                
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
        logger.debug(f"Created task object: {task}")

        if task.duration_id:
            logger.debug(f"Task has duration_id {task.duration_id}, calculating deadline")
            duration = await self.session.get(DurationSetting, task.duration_id)
            if duration:
                task.deadline = await duration.calculate_deadline_async(self.session)
                logger.debug(f"Calculated deadline: {task.deadline}")
            else:
                logger.warning(f"Duration {task.duration_id} not found")

        logger.debug("Adding task to session")
        self.session.add(task)
        logger.debug("Committing session")
        await self.session.commit()
        logger.debug("Refreshing task")
        await self.session.refresh(task)
        logger.debug(f"Task created with ID: {task.id}")

        return await self._task_to_dict(task)

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
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        return await self._task_to_dict(task)

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

    async def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Преобразовать задачу в словарь"""
        logger.debug(f"Converting task {task.id} to dict")
        logger.debug(f"Task duration_id: {task.duration_id}")
        logger.debug(f"Task deadline: {task.deadline}")
        
        try:
            # Загружаем связанные объекты заранее
            if task.type_id:
                type_query = select(TaskTypeSetting).where(TaskTypeSetting.id == task.type_id)
                type_result = await self.session.execute(type_query)
                task_type = type_result.scalar_one_or_none()
            else:
                task_type = None
                
            if task.status_id:
                status_query = select(StatusSetting).where(StatusSetting.id == task.status_id)
                status_result = await self.session.execute(status_query)
                status = status_result.scalar_one_or_none()
            else:
                status = None
                
            if task.priority_id:
                priority_query = select(PrioritySetting).where(PrioritySetting.id == task.priority_id)
                priority_result = await self.session.execute(priority_query)
                priority = priority_result.scalar_one_or_none()
            else:
                priority = None
                
            # Подготовим данные о длительности, если она есть
            duration_data = None
            if task.duration_id:
                try:
                    duration_query = select(DurationSetting).where(DurationSetting.id == task.duration_id)
                    duration_result = await self.session.execute(duration_query)
                    duration = duration_result.scalar_one_or_none()
                    
                    if duration:
                        duration_data = {
                            'id': duration.id,
                            'name': duration.name,
                            'type': duration.duration_type.value if duration.duration_type else None,
                            'value': duration.value
                        }
                        logger.debug(f"Duration data: {duration_data}")
                except Exception as e:
                    logger.exception(f"Error preparing duration data: {e}")
                    duration_data = None
            
            result = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'type': {
                    'id': task_type.id,
                    'name': task_type.name,
                    'color': task_type.color
                } if task_type else None,
                'status': {
                    'id': status.id,
                    'name': status.name,
                    'color': status.color,
                    'order': status.order
                } if status else None,
                'priority': {
                    'id': priority.id,
                    'name': priority.name,
                    'color': priority.color,
                    'order': priority.order
                } if priority else None,
                'duration': duration_data,
                'deadline': task.deadline.isoformat() if task.deadline else None,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'is_overdue': task.is_overdue()
            }
            logger.debug(f"Task {task.id} converted to dict successfully")
            return result
        except Exception as e:
            logger.exception(f"Error converting task {task.id} to dict: {e}")
            raise 