from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging
import asyncio
from datetime import datetime

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
    ) -> list[Any] | tuple[Any]:
        """Получить список задач пользователя с фильтрами"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return []

        query = select(Task).where(Task.user_id == user.telegram_id) # type: ignore

        if filters:
            if filters.get('id'):
                query = query.where(Task.id == filters['id'])
            if filters.get('status_id'):
                query = query.where(Task.status_id == int(filters['status_id']))
            if filters.get('priority_id'):
                query = query.where(Task.priority_id == int(filters['priority_id']))
            if filters.get('duration_id'):
                query = query.where(Task.duration_id == int(filters['duration_id']))
            if filters.get('type_id'):
                query = query.where(Task.type_id == int(filters['type_id']))
            
            # Фильтрация по завершенным/незавершенным задачам
            if 'is_completed' in filters:
                if filters['is_completed'] is False:
                    # Показываем только незавершенные задачи (completed_at is NULL)
                    query = query.where(Task.completed_at == None)
                elif filters['is_completed'] is True:
                    # Показываем только завершенные задачи (completed_at is NOT NULL)
                    query = query.where(Task.completed_at != None)
            
            # Добавляем фильтрацию по дедлайну
            deadline_conditions = []
            if filters.get('deadline_from'):
                deadline_from = datetime.strptime(filters['deadline_from'], '%Y-%m-%d')
                # Устанавливаем время на начало дня (00:00:00)
                deadline_from = deadline_from.replace(hour=0, minute=0, second=0, microsecond=0)
                deadline_conditions.append(Task.deadline >= deadline_from)
            if filters.get('deadline_to'):
                deadline_to = datetime.strptime(filters['deadline_to'], '%Y-%m-%d')
                # Устанавливаем время на конец дня (23:59:59)
                deadline_to = deadline_to.replace(hour=23, minute=59, second=59, microsecond=999999)
                deadline_conditions.append(Task.deadline <= deadline_to)
            if deadline_conditions:
                query = query.where(and_(*deadline_conditions))

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

    async def get_tasks_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search_query: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Получить список задач пользователя с пагинацией, сортировкой и поиском
        
        Args:
            user_id: ID пользователя
            page: Номер страницы (начиная с 1)
            page_size: Количество задач на странице
            filters: Словарь с фильтрами (status_id, priority_id, duration_id, type_id)
            sort_by: Поле для сортировки (title, deadline, priority, status)
            sort_order: Порядок сортировки (asc, desc)
            search_query: Строка для поиска в названии и описании задачи
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: Список задач и общее количество задач
        """
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return [], 0
            
        # Получаем все задачи с фильтрами
        all_tasks = await self.get_tasks(user_id, filters)
        
        # Применяем поиск, если указан
        if search_query and search_query.strip():
            search_query = search_query.lower()
            filtered_tasks = []
            for task in all_tasks:
                title = task['title'].lower()
                description = task['description'].lower() if task['description'] else ""
                
                if search_query in title or search_query in description:
                    filtered_tasks.append(task)
            all_tasks = filtered_tasks
        
        # Применяем сортировку, если указана
        if sort_by:
            reverse = sort_order.lower() == "desc"
            
            if sort_by == "title":
                all_tasks.sort(key=lambda x: x['title'].lower(), reverse=reverse)
            elif sort_by == "deadline":
                # Сортируем по дедлайну, задачи без дедлайна в конце
                all_tasks.sort(
                    key=lambda x: (x['deadline'] is None, x['deadline']), 
                    reverse=reverse
                )
            elif sort_by == "priority":
                # Сортируем по приоритету, задачи без приоритета в конце
                all_tasks.sort(
                    key=lambda x: (
                        x['priority'] is None, 
                        -x['priority']['order'] if x['priority'] else 0
                    ), 
                    reverse=reverse
                )
            elif sort_by == "status":
                # Сортируем по статусу, задачи без статуса в конце
                all_tasks.sort(
                    key=lambda x: (
                        x['status'] is None, 
                        x['status']['order'] if x['status'] else 0
                    ), 
                    reverse=reverse
                )
        
        # Получаем общее количество задач
        total_tasks = len(all_tasks)
        
        # Вычисляем смещение для пагинации
        offset = (page - 1) * page_size
        
        # Получаем задачи для текущей страницы
        paginated_tasks = all_tasks[offset:offset + page_size] if offset < total_tasks else []
        
        return paginated_tasks, total_tasks
        
    async def search_tasks(
        self,
        user_id: str,
        search_query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск задач по названию и описанию
        
        Args:
            user_id: ID пользователя
            search_query: Строка для поиска
            filters: Словарь с фильтрами (status_id, priority_id, duration_id, type_id)
            
        Returns:
            List[Dict[str, Any]]: Список найденных задач
        """
        if not search_query.strip():
            return []
            
        # Получаем все задачи с фильтрами
        all_tasks = await self.get_tasks(user_id, filters)
        
        # Применяем поиск
        search_query = search_query.lower()
        found_tasks = []
        
        for task in all_tasks:
            title = task['title'].lower()
            description = task['description'].lower() if task['description'] else ""
            
            if search_query in title or search_query in description:
                found_tasks.append(task)
                
        return found_tasks
        
    async def get_task_count(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        search_query: Optional[str] = None
    ) -> int:
        """
        Получить общее количество задач пользователя с учетом фильтров и поиска
        
        Args:
            user_id: ID пользователя
            filters: Словарь с фильтрами (status_id, priority_id, duration_id, type_id)
            search_query: Строка для поиска в названии и описании задачи
            
        Returns:
            int: Общее количество задач
        """
        # Если есть поисковый запрос, используем метод search_tasks
        if search_query and search_query.strip():
            tasks = await self.search_tasks(user_id, search_query, filters)
            return len(tasks)
            
        # Иначе получаем количество задач с фильтрами
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return 0
            
        query = select(func.count()).select_from(Task).where(Task.user_id == user.telegram_id) # type: ignore
        
        if filters:
            if filters.get('status_id'):
                query = query.where(Task.status_id == int(filters['status_id']))
            if filters.get('priority_id'):
                query = query.where(Task.priority_id == int(filters['priority_id']))
            if filters.get('duration_id'):
                query = query.where(Task.duration_id == int(filters['duration_id']))
            if filters.get('type_id'):
                query = query.where(Task.type_id == int(filters['type_id']))
            
            # Фильтрация по завершенным/незавершенным задачам
            if 'is_completed' in filters:
                if filters['is_completed'] is False:
                    # Показываем только незавершенные задачи (completed_at is NULL)
                    query = query.where(Task.completed_at == None)
                elif filters['is_completed'] is True:
                    # Показываем только завершенные задачи (completed_at is NOT NULL)
                    query = query.where(Task.completed_at != None)
            
            # Добавляем фильтрацию по дедлайну
            deadline_conditions = []
            if filters.get('deadline_from'):
                deadline_from = datetime.strptime(filters['deadline_from'], '%Y-%m-%d')
                # Устанавливаем время на начало дня (00:00:00)
                deadline_from = deadline_from.replace(hour=0, minute=0, second=0, microsecond=0)
                deadline_conditions.append(Task.deadline >= deadline_from)
            if filters.get('deadline_to'):
                deadline_to = datetime.strptime(filters['deadline_to'], '%Y-%m-%d')
                # Устанавливаем время на конец дня (23:59:59)
                deadline_to = deadline_to.replace(hour=23, minute=59, second=59, microsecond=999999)
                deadline_conditions.append(Task.deadline <= deadline_to)
            if deadline_conditions:
                query = query.where(and_(*deadline_conditions))
                
        result = await self.session.execute(query)
        count = result.scalar()
        
        return count or 0

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
                TaskTypeSetting.id == int(task_data['type_id']), # type: ignore
                TaskTypeSetting.user_id == user.telegram_id # type: ignore
            )
            type_result = await self.session.execute(type_query)
            if not type_result.scalar_one_or_none():
                logger.error(f"Type {task_data['type_id']} does not belong to user {user_id}")
                return None
            logger.debug(f"Type {task_data['type_id']} belongs to user {user_id}")

        # Получаем настройки по умолчанию, если они не указаны
        if not task_data.get('status_id'):
            status_query = select(StatusSetting).where(
                StatusSetting.user_id == user.telegram_id, # type: ignore
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
                PrioritySetting.user_id == user.telegram_id, # type: ignore
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
                TaskTypeSetting.user_id == user.telegram_id, # type: ignore
                TaskTypeSetting.is_default == True
            )
            type_result = await self.session.execute(type_query)
            task_type = type_result.scalar_one_or_none()
            if task_type:
                task_data['type_id'] = task_type.id

        # Обрабатываем deadline, если он пришел в строковом формате
        deadline = task_data.get('deadline')
        if isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                logger.debug(f"Converted deadline string to datetime: {deadline}")
                task_data['deadline'] = deadline
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting deadline: {e}")

        task = Task(
            user_id=user.telegram_id,
            title=task_data['title'],
            description=task_data.get('description'),
            type_id=int(task_data.get('type_id')),
            priority_id=int(task_data.get('priority_id')),
            duration_id=int(task_data.get('duration_id')),
            deadline=task_data.get('deadline')
        )
        logger.debug(f"Created task object: {task}")

        # Устанавливаем статус и проверяем, является ли он финальным
        if task_data.get('status_id'):
            status_query = select(StatusSetting).where(StatusSetting.id == int(task_data['status_id'])) # type: ignore
            status_result = await self.session.execute(status_query)
            status = status_result.scalar_one_or_none()
            if status:
                task.change_status(status)
            else:
                task.status_id = task_data.get('status_id')

        if task.duration_id and not task.deadline:
            logger.debug(f"Task has duration_id {task.duration_id}, calculating deadline")
            duration = await self.session.get(DurationSetting, int(task.duration_id))
            if duration:
                task.deadline = await duration.calculate_deadline_async(self.session)
                logger.debug(f"Calculated deadline: {task.deadline}")
            else:
                logger.warning(f"Duration {task.duration_id} not found")
        elif task.deadline:
            logger.debug(f"Using manually set deadline: {task.deadline}")

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
                TaskTypeSetting.id == int(task_data['type_id']), # type: ignore
                TaskTypeSetting.user_id == user.telegram_id # type: ignore
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
            # Получаем новый статус
            status_query = select(StatusSetting).where(StatusSetting.id == int(task_data['status_id'])) # type: ignore
            status_result = await self.session.execute(status_query)
            new_status = status_result.scalar_one_or_none()
            
            if new_status:
                # Используем метод change_status для обновления статуса и completed_at
                task.change_status(new_status)
            else:
                # Если статус не найден, просто обновляем status_id
                task.status_id = task_data['status_id']
        if 'priority_id' in task_data:
            task.priority_id = task_data['priority_id']
        if 'completed_at' in task_data:
            task.completed_at = task_data['completed_at']
        if 'deadline' in task_data:
            # Преобразуем строковое значение deadline в datetime
            deadline_value = task_data['deadline']
            if isinstance(deadline_value, str):
                try:
                    deadline_value = datetime.fromisoformat(deadline_value.replace('Z', '+00:00'))
                    logger.debug(f"Converted deadline string to datetime: {deadline_value}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting deadline: {e}")
            task.deadline = deadline_value
            logger.debug(f"Manually updating deadline to: {task.deadline}")
        if 'duration_id' in task_data:
            task.duration_id = task_data['duration_id']
            # Вычисляем дедлайн на основе продолжительности только если дедлайн не задан вручную
            if task.duration_id and 'deadline' not in task_data:
                duration = await self.session.get(DurationSetting, int(task.duration_id))
                if duration:
                    task.deadline = await duration.calculate_deadline_async(self.session)
                    logger.debug(f"Calculated deadline based on duration: {task.deadline}")
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
                type_query = select(TaskTypeSetting).where(TaskTypeSetting.id == int(task.type_id)) # type: ignore
                type_result = await self.session.execute(type_query)
                task_type = type_result.scalar_one_or_none()
            else:
                task_type = None
                
            if task.status_id:
                status_query = select(StatusSetting).where(StatusSetting.id == int(task.status_id)) # type: ignore
                status_result = await self.session.execute(status_query)
                status = status_result.scalar_one_or_none()
            else:
                status = None
                
            if task.priority_id:
                priority_query = select(PrioritySetting).where(PrioritySetting.id == int(task.priority_id)) # type: ignore
                priority_result = await self.session.execute(priority_query)
                priority = priority_result.scalar_one_or_none()
            else:
                priority = None
                
            # Подготовим данные о длительности, если она есть
            duration_data = None
            if task.duration_id:
                try:
                    duration_query = select(DurationSetting).where(DurationSetting.id == int(task.duration_id)) # type: ignore
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
                'deadline': task.deadline.strftime('%d.%m.%Y %H:%M') if task.deadline else None,
                'deadline_iso': task.deadline.isoformat() if task.deadline else None,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'is_overdue': task.is_overdue()
            }
            logger.debug(f"Task {task.id} converted to dict successfully")
            return result
        except Exception as e:
            logger.exception(f"Error converting task {task.id} to dict: {e}")
            raise 