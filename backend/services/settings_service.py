import json
import logging
from typing import Dict, Any, List, Optional, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    DefaultSettings, StatusSetting, PrioritySetting, 
    DurationSetting, TaskTypeSetting, DurationType, User
)
from backend.services.auth_service import AuthService
from backend.models.settings import Settings
from backend.models.status import Status
from backend.models.priority import Priority
from backend.models.duration import Duration
from backend.models.task_type import TaskType

logger = logging.getLogger(__name__)

class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_service = AuthService(session)

    async def get_settings(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Получить все настройки пользователя
        
        Args:
            user_id: ID пользователя. Если не указан, возвращаются настройки по умолчанию.
        
        Returns:
            Dict[str, Any]: Словарь с настройками пользователя
        """

        # Если указан ID пользователя, пробуем получить пользовательские настройки
        if user_id:
            logger.debug(f"Получение настроек для пользователя {user_id}")
            user = await self.auth_service.get_user_by_id(user_id)
            
            if user:
                logger.debug(f"Пользователь {user_id} найден, получаем его настройки")
                
                # Получаем пользовательские настройки
                statuses = await self.get_statuses(user_id)
                logger.debug(f"Получены статусы: {len(statuses)}")

                priorities = await self.get_priorities(user_id)
                logger.debug(f"Получены приоритеты: {len(priorities)}")

                durations = await self.get_durations(user_id)
                logger.debug(f"Получены длительности: {len(durations)}")

                task_types = await self.get_task_types(user_id)
                logger.debug(f"Получены типы задач: {len(task_types)}")

                # Если у пользователя есть хотя бы одна настройка, возвращаем их
                if statuses or priorities or durations or task_types:
                    logger.debug(f"Найдены пользовательские настройки для пользователя {user_id}")
                    result = {
                        "statuses": statuses,
                        "priorities": priorities,
                        "durations": durations,
                        "task_types": task_types
                    }
                    logger.debug(f"Возвращаем настройки: {result}")
                    return result
                else:
                    logger.debug(f"Пользовательские настройки не найдены для пользователя {user_id}, возвращаем настройки по умолчанию")
            else:
                logger.warning(f"Пользователь {user_id} не найден, возвращаем настройки по умолчанию")
        else:
            logger.debug("ID пользователя не указан, возвращаем настройки по умолчанию")

        # Получаем все настройки по умолчанию
        default_statuses = await self.session.execute(
            select(DefaultSettings).where(
                DefaultSettings.setting_type == "status",
                DefaultSettings.is_active == True
            )
        )
        default_priorities = await self.session.execute(
            select(DefaultSettings).where(
                DefaultSettings.setting_type == "priority",
                DefaultSettings.is_active == True
            )
        )
        default_durations = await self.session.execute(
            select(DefaultSettings).where(
                DefaultSettings.setting_type == "duration",
                DefaultSettings.is_active == True
            )
        )
        default_task_types = await self.session.execute(
            select(DefaultSettings).where(
                DefaultSettings.setting_type == "task_type",
                DefaultSettings.is_active == True
            )
        )

        logger.debug("Возвращаем настройки по умолчанию")
        return {
            "statuses": [json.loads(status.value) for status in default_statuses.scalars()],
            "priorities": [json.loads(priority.value) for priority in default_priorities.scalars()],
            "durations": [json.loads(duration.value) for duration in default_durations.scalars()],
            "task_types": [json.loads(task_type.value) for task_type in default_task_types.scalars()]
        }

    async def get_task_types(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить список типов задач пользователя"""
        logger.debug(f"Получение типов задач для пользователя {user_id}")

        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        # Сначала пробуем получить пользовательские настройки
        result = await self.session.execute(
            select(TaskTypeSetting).where(
                TaskTypeSetting.user_id == user.telegram_id, # type: ignore
                TaskTypeSetting.is_active == True
            ).order_by(TaskTypeSetting.order)
        )
        task_types = list(result.scalars())

        logger.debug(f"Найдено {len(task_types)} пользовательских типов задач для пользователя {user_id}")

        # Если пользовательских настроек нет, берем настройки по умолчанию
        if not task_types:
            logger.debug(f"Пользовательские типы задач не найдены, получаем типы задач по умолчанию")
            default_task_types = await self.session.execute(
                select(DefaultSettings).where(
                    DefaultSettings.setting_type == "task_type",
                    DefaultSettings.is_active == True
                )
            )

            # Используем ID из базы данных
            default_task_types_list = []
            for task_type in default_task_types.scalars():
                task_type_data = json.loads(task_type.value)
                # Используем ID записи из таблицы DefaultSettings
                task_type_data["id"] = task_type.id
                default_task_types_list.append(task_type_data)

            logger.debug(f"Найдено {len(default_task_types_list)} типов задач по умолчанию")
            return default_task_types_list

        return [
            {
                "id": task_type.id,
                "name": task_type.name,
                "description": task_type.description,
                "color": task_type.color,
                "order": task_type.order,
                "is_default": task_type.is_default,
                "is_active": task_type.is_active
            }
            for task_type in task_types
        ]

    async def create_task_type(
        self,
        user_id: str,
        task_type_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Создать новый тип задачи"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        task_type = TaskTypeSetting(
            user_id=user.id,
            name=task_type_data["name"],
            description=task_type_data.get("description"),
            color=task_type_data.get("color"),
            order=task_type_data.get("order", 0),
            is_default=task_type_data.get("is_default", False),
            is_active=task_type_data.get("is_active", True)
        )

        self.session.add(task_type)
        await self.session.commit()
        await self.session.refresh(task_type)

        return {
            "id": task_type.id,
            "name": task_type.name,
            "description": task_type.description,
            "color": task_type.color,
            "order": task_type.order,
            "is_default": task_type.is_default,
            "is_active": task_type.is_active
        }

    async def update_task_type(
        self,
        user_id: str,
        task_type_id: int,
        task_type_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Обновить тип задачи"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        task_type = await self.session.get(TaskTypeSetting, task_type_id)
        if not task_type or task_type.user_id != user.id:
            return None

        if "name" in task_type_data:
            task_type.name = task_type_data["name"]
        if "description" in task_type_data:
            task_type.description = task_type_data["description"]
        if "color" in task_type_data:
            task_type.color = task_type_data["color"]
        if "order" in task_type_data:
            task_type.order = task_type_data["order"]
        if "is_default" in task_type_data:
            task_type.is_default = task_type_data["is_default"]
        if "is_active" in task_type_data:
            task_type.is_active = task_type_data["is_active"]

        await self.session.commit()
        await self.session.refresh(task_type)

        return {
            "id": task_type.id,
            "name": task_type.name,
            "description": task_type.description,
            "color": task_type.color,
            "order": task_type.order,
            "is_default": task_type.is_default,
            "is_active": task_type.is_active
        }

    async def delete_task_type(self, user_id: str, task_type_id: int) -> bool:
        """Удалить тип задачи"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return False

        task_type = await self.session.get(TaskTypeSetting, task_type_id)
        if not task_type or task_type.user_id != user.id:
            return False

        await self.session.delete(task_type)
        await self.session.commit()

        return True

    async def create_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Создать новую настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return None

        if setting_type == 'status':
            setting = StatusSetting(
                user_id=user.id,
                name=setting_data['name'],
                code=setting_data['code'],
                color=setting_data.get('color', '#808080'),
                order=setting_data.get('order', 0),
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False),
                is_final=setting_data.get('is_final', False)
            )
        elif setting_type == 'priority':
            setting = PrioritySetting(
                user_id=user.id,
                name=setting_data['name'],
                color=setting_data.get('color', '#808080'),
                order=setting_data.get('order', 0),
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False)
            )
        else:  # duration
            setting = DurationSetting(
                user_id=user.id,
                name=setting_data['name'],
                duration_type=DurationType(setting_data['type']),
                value=setting_data['value'],
                is_active=setting_data.get('is_active', True),
                is_default=setting_data.get('is_default', False)
            )

        self.session.add(setting)
        await self.session.commit()
        await self.session.refresh(setting)

        return setting.to_dict()

    async def update_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_id: int,
        setting_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Обновить настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return None

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return None

        setting = await self.session.get(setting_class, setting_id)
        if not setting or setting.user_id != user.id:
            return None

        if setting_type == 'status':
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'code' in setting_data:
                setting.code = setting_data['code']
            if 'color' in setting_data:
                setting.color = setting_data['color']
            if 'order' in setting_data:
                setting.order = setting_data['order']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']
            if 'is_final' in setting_data:
                setting.is_final = setting_data['is_final']
        elif setting_type == 'priority':
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'color' in setting_data:
                setting.color = setting_data['color']
            if 'order' in setting_data:
                setting.order = setting_data['order']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']
        else:  # duration
            if 'name' in setting_data:
                setting.name = setting_data['name']
            if 'type' in setting_data:
                setting.duration_type = DurationType(setting_data['type'])
            if 'value' in setting_data:
                setting.value = setting_data['value']
            if 'is_active' in setting_data:
                setting.is_active = setting_data['is_active']
            if 'is_default' in setting_data:
                setting.is_default = setting_data['is_default']

        await self.session.commit()
        await self.session.refresh(setting)

        return setting.to_dict()

    async def delete_setting(
        self,
        user_id: str,
        setting_type: str,
        setting_id: int
    ) -> bool:
        """Удалить настройку"""
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return False

        setting_class = self._get_setting_class(setting_type)
        if not setting_class:
            return False

        setting = await self.session.get(setting_class, setting_id)
        if not setting or setting.user_id != user.id:
            return False

        await self.session.delete(setting)
        await self.session.commit()

        return True

    def _get_setting_class(self, setting_type: str) -> Optional[Type]:
        """Получить класс настройки по типу"""
        setting_classes = {
            'status': StatusSetting,
            'priority': PrioritySetting,
            'duration': DurationSetting
        }
        return setting_classes.get(setting_type)

    async def get_settings_from_models(self):
        # Получаем все настройки
        result = await self.session.execute(select(Settings))
        settings = result.scalar_one_or_none()

        if not settings:
            # Создаем настройки по умолчанию
            settings = Settings()
            self.session.add(settings)
            await self.session.commit()

        # Получаем статусы
        result = await self.session.execute(select(Status))
        statuses = result.scalars().all()

        # Получаем приоритеты
        result = await self.session.execute(select(Priority))
        priorities = result.scalars().all()

        # Получаем длительности
        result = await self.session.execute(select(Duration))
        durations = result.scalars().all()

        # Получаем типы задач
        result = await self.session.execute(select(TaskType))
        task_types = result.scalars().all()

        return {
            'statuses': [{"id": s.id, "name": s.name} for s in statuses],
            'priorities': [{"id": p.id, "name": p.name} for p in priorities],
            'durations': [{"id": d.id, "name": d.name} for d in durations],
            'task_types': [{"id": t.id, "name": t.name} for t in task_types],
        }

    async def create_default_settings(self):
        # Создаем статусы по умолчанию
        default_statuses = [
            Status(name="Новая"),
            Status(name="В процессе"),
            Status(name="Завершена"),
            Status(name="Отменена"),
        ]
        for status in default_statuses:
            self.session.add(status)

        # Создаем приоритеты по умолчанию
        default_priorities = [
            Priority(name="Высокий"),
            Priority(name="Средний"),
            Priority(name="Низкий"),
        ]
        for priority in default_priorities:
            self.session.add(priority)

        # Создаем длительности по умолчанию
        default_durations = [
            Duration(name="День"),
            Duration(name="Неделя"),
            Duration(name="Месяц"),
            Duration(name="Квартал"),
            Duration(name="Год"),
        ]
        for duration in default_durations:
            self.session.add(duration)

        # Создаем типы задач по умолчанию
        default_task_types = [
            TaskType(name="Личные", description="Личные задачи"),
            TaskType(name="Семейные", description="Семейные задачи"),
            TaskType(name="Рабочие", description="Рабочие задачи"),
            TaskType(name="Для отдыха", description="Задачи для отдыха"),
        ]
        for task_type in default_task_types:
            self.session.add(task_type)

        # Создаем настройки по умолчанию
        settings = Settings()
        self.session.add(settings)

        await self.session.commit()

    async def get_statuses(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить список статусов пользователя"""
        logger.debug(f"Получение статусов для пользователя {user_id}")

        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        # Сначала пробуем получить пользовательские настройки
        result = await self.session.execute(
            select(StatusSetting).where(
                StatusSetting.user_id == user.telegram_id, # type: ignore
                StatusSetting.is_active == True
            ).order_by(StatusSetting.order)
        )
        statuses = list(result.scalars())

        logger.debug(f"Найдено {len(statuses)} пользовательских статусов для пользователя {user_id}")

        # Если пользовательских настроек нет, берем настройки по умолчанию
        if not statuses:
            logger.debug(f"Пользовательские статусы не найдены, получаем статусы по умолчанию")
            default_statuses = await self.session.execute(
                select(DefaultSettings).where(
                    DefaultSettings.setting_type == "status",
                    DefaultSettings.is_active == True
                )
            )

            # Используем ID из базы данных
            default_statuses_list = []
            for status in default_statuses.scalars():
                status_data = json.loads(status.value)
                # Используем ID записи из таблицы DefaultSettings
                status_data["id"] = status.id
                default_statuses_list.append(status_data)

            logger.debug(f"Найдено {len(default_statuses_list)} статусов по умолчанию")
            return default_statuses_list

        return [
            {
                "id": status.id,
                "name": status.name,
                "code": status.code,
                "color": status.color,
                "order": status.order,
                "is_default": status.is_default,
                "is_final": status.is_final,
                "is_active": status.is_active
            }
            for status in statuses
        ]

    async def get_priorities(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить список приоритетов пользователя"""
        logger.debug(f"Получение приоритетов для пользователя {user_id}")

        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        # Сначала пробуем получить пользовательские настройки
        result = await self.session.execute(
            select(PrioritySetting).where(
                PrioritySetting.user_id == user.telegram_id, # type: ignore
                PrioritySetting.is_active == True
            ).order_by(PrioritySetting.order)
        )
        priorities = list(result.scalars())

        logger.debug(f"Найдено {len(priorities)} пользовательских приоритетов для пользователя {user_id}")

        # Если пользовательских настроек нет, берем настройки по умолчанию
        if not priorities:
            logger.debug(f"Пользовательские приоритеты не найдены, получаем приоритеты по умолчанию")
            default_priorities = await self.session.execute(
                select(DefaultSettings).where(
                    DefaultSettings.setting_type == "priority",
                    DefaultSettings.is_active == True
                )
            )

            # Используем ID из базы данных
            default_priorities_list = []
            for priority in default_priorities.scalars():
                priority_data = json.loads(priority.value)
                # Используем ID записи из таблицы DefaultSettings
                priority_data["id"] = priority.id
                default_priorities_list.append(priority_data)

            logger.debug(f"Найдено {len(default_priorities_list)} приоритетов по умолчанию")
            return default_priorities_list

        return [
            {
                "id": priority.id,
                "name": priority.name,
                "color": priority.color,
                "order": priority.order,
                "is_default": priority.is_default,
                "is_active": priority.is_active
            }
            for priority in priorities
        ]

    async def get_durations(self, user_id: str) -> List[Dict[str, Any]]:
        """Получить список длительностей пользователя"""
        logger.debug(f"Получение длительностей для пользователя {user_id}")
        
        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        # Сначала пробуем получить пользовательские настройки
        result = await self.session.execute(
            select(DurationSetting).where(
                DurationSetting.user_id == user.telegram_id, # type: ignore
                DurationSetting.is_active == True
            ).order_by(DurationSetting.id)
        )
        durations = list(result.scalars())

        logger.debug(f"Найдено {len(durations)} пользовательских приоритетов для пользователя {user_id}")

        # Если пользовательских настроек нет, берем настройки по умолчанию
        if not durations:
            # Получаем настройки по умолчанию
            default_durations = await self.session.execute(
                select(DefaultSettings).where(
                    DefaultSettings.setting_type == "duration",
                    DefaultSettings.is_active == True
                )
            )

            # Создаем список длительностей с уникальными идентификаторами
            default_durations_list = []
            for duration in default_durations.scalars():
                duration_data = json.loads(duration.value)
                # Используем ID записи из таблицы DefaultSettings
                duration_data["id"] = duration.id

                # Проверяем, что duration_type существует и является строкой
                if "duration_type" in duration_data and isinstance(duration_data["duration_type"], str):
                    # Оставляем duration_type как есть, это строковое значение из перечисления
                    pass

                default_durations_list.append(duration_data)
        
            logger.debug(f"Найдено {len(default_durations_list)} длительностей по умолчанию")
            return default_durations_list
        return [
            {
                "id": duration.id,
                "name": duration.name,
                "type": duration.duration_type.value,
                "value": duration.value,
                "is_default": duration.is_default,
                "is_active": duration.is_active
            }
            for duration in durations
        ]

    async def get_user_settings(self, user_id: str):
        """Получить пользователя по ID"""
        query = select(User.settings).where(User.telegram_id == int(user_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def save_user_preferences(self, user_id: str, preferences: dict) -> bool:
        """Сохранение настроек пользователя."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == int(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return False

        user.settings = json.dumps(preferences)
        # Сохраняем изменения
        logger.info(f"Сохранение настроек пользователя {user_id}: {user.settings}")
        self.session.add(user)
        await self.session.commit()

        return True
