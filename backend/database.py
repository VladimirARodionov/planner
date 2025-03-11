from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import json
import logging

from backend.create_bot import db_string
from backend.db.models import DurationType, DefaultSettings, GlobalSettings, StatusSetting, PrioritySetting, DurationSetting, TaskTypeSetting



# Создаем асинхронный движок SQLAlchemy
engine = create_async_engine(db_string, echo=True)
logger = logging.getLogger(__name__)

# Создаем фабрику асинхронных сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@asynccontextmanager
async def get_session() -> AsyncSession:
    """Получить асинхронную сессию базы данных"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Функция для инициализации базы данных
async def init_db():
    # Создаем настройки по умолчанию, если их еще нет
    async with async_session() as session:
        # Проверяем, есть ли уже настройки по умолчанию
        default_settings_count = await session.execute(select(DefaultSettings))
        if default_settings_count.first() is None:
            await create_initial_default_settings(session)
        
        # Проверяем, есть ли глобальные настройки
        global_settings_count = await session.execute(select(GlobalSettings))
        if global_settings_count.first() is None:
            await create_initial_global_settings(session)

# Функция для создания начальных глобальных настроек
async def create_initial_global_settings(session: AsyncSession):
    # Создаем базовые глобальные настройки
    global_settings = [
        {
            "key": "reminder_check_interval",
            "value": "300",  # 5 минут в секундах
            "description": "Интервал проверки напоминаний в секундах"
        },
        {
            "key": "max_tasks_per_user",
            "value": "100",
            "description": "Максимальное количество задач на пользователя"
        },
        {
            "key": "max_reminders_per_task",
            "value": "5",
            "description": "Максимальное количество напоминаний на задачу"
        },
        {
            "key": "default_language",
            "value": "ru",
            "description": "Язык по умолчанию"
        }
    ]
    
    for setting in global_settings:
        db_setting = GlobalSettings(
            key=setting["key"],
            value=setting["value"],
            description=setting["description"]
        )
        session.add(db_setting)
    
    await session.commit()

# Функция для создания начальных настроек по умолчанию
async def create_initial_default_settings(session: AsyncSession):
    logger.debug("Создание настроек по умолчанию")
    
    # Создаем стандартные статусы
    default_statuses = [
        {
            "id": 1,
            "name": "Ожидает выполнения",
            "code": "pending",
            "color": "#808080",  # Серый
            "order": 1,
            "is_default": True,
            "is_final": False,
            "is_active": True
        },
        {
            "id": 2,
            "name": "В процессе",
            "code": "in_progress",
            "color": "#FFA500",  # Оранжевый
            "order": 2,
            "is_default": False,
            "is_final": False,
            "is_active": True
        },
        {
            "id": 3,
            "name": "На проверке",
            "code": "review",
            "color": "#4169E1",  # Синий
            "order": 3,
            "is_default": False,
            "is_final": False,
            "is_active": True
        },
        {
            "id": 4,
            "name": "Выполнено",
            "code": "completed",
            "color": "#008000",  # Зеленый
            "order": 4,
            "is_default": False,
            "is_final": True,
            "is_active": True
        },
        {
            "id": 5,
            "name": "Отменено",
            "code": "cancelled",
            "color": "#FF0000",  # Красный
            "order": 5,
            "is_default": False,
            "is_final": True,
            "is_active": True
        }
    ]
    
    for status in default_statuses:
        db_setting = DefaultSettings(
            setting_type="status",
            name=status["name"],
            value=json.dumps(status),
            is_active=True
        )
        session.add(db_setting)
    
    # Создаем стандартные приоритеты
    default_priorities = [
        {
            "id": 1,
            "name": "Срочно и важно",
            "color": "#FF0000",
            "order": 1,
            "is_default": True,
            "is_active": True
        },
        {
            "id": 2,
            "name": "Важно, не срочно",
            "color": "#FFA500",
            "order": 2,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 3,
            "name": "Срочно, не важно",
            "color": "#FFFF00",
            "order": 3,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 4,
            "name": "Не срочно и не важно",
            "color": "#00FF00",
            "order": 4,
            "is_default": False,
            "is_active": True
        }
    ]
    
    for priority in default_priorities:
        db_setting = DefaultSettings(
            setting_type="priority",
            name=priority["name"],
            value=json.dumps(priority),
            is_active=True
        )
        session.add(db_setting)
    
    # Создаем стандартные продолжительности
    default_durations = [
        {
            "id": 1,
            "name": "На день",
            "duration_type": DurationType.DAYS.name,
            "value": 1,
            "is_default": True,
            "is_active": True
        },
        {
            "id": 2,
            "name": "На неделю",
            "duration_type": DurationType.WEEKS.name,
            "value": 1,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 3,
            "name": "На месяц",
            "duration_type": DurationType.MONTHS.name,
            "value": 1,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 4,
            "name": "На год",
            "duration_type": DurationType.YEARS.name,
            "value": 1,
            "is_default": False,
            "is_active": True
        }
    ]
    
    for duration in default_durations:
        db_setting = DefaultSettings(
            setting_type="duration",
            name=duration["name"],
            value=json.dumps(duration),
            is_active=True
        )
        session.add(db_setting)

    # Создаем типы задач по умолчанию
    default_task_types = [
        {
            "id": 1,
            "name": "Личные",
            "description": "Личные задачи и дела",
            "color": "#FF69B4",  # Розовый
            "order": 1,
            "is_default": True,
            "is_active": True
        },
        {
            "id": 2,
            "name": "Семейные",
            "description": "Задачи, связанные с семьей",
            "color": "#4169E1",  # Синий
            "order": 2,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 3,
            "name": "Рабочие",
            "description": "Рабочие задачи и проекты",
            "color": "#32CD32",  # Зеленый
            "order": 3,
            "is_default": False,
            "is_active": True
        },
        {
            "id": 4,
            "name": "Для отдыха",
            "description": "Задачи для отдыха и развлечений",
            "color": "#FFA500",  # Оранжевый
            "order": 4,
            "is_default": False,
            "is_active": True
        }
    ]

    for task_type in default_task_types:
        db_setting = DefaultSettings(
            setting_type="task_type",
            name=task_type["name"],
            value=json.dumps(task_type),
            is_active=True
        )
        session.add(db_setting)
    
    await session.commit()
    logger.debug("Настройки по умолчанию успешно созданы")

# Функция для создания настроек пользователя на основе настроек по умолчанию
async def create_user_settings(user_id: int, session: AsyncSession):
    logger.debug(f"Создание настроек для пользователя {user_id}")
    
    # Проверяем, есть ли уже настройки у пользователя
    existing_statuses = await session.execute(
        select(StatusSetting).where(StatusSetting.user_id == user_id)
    )
    if existing_statuses.first() is not None:
        logger.debug(f"У пользователя {user_id} уже есть настройки, пропускаем создание")
        return
    
    # Проверяем, есть ли настройки по умолчанию
    default_settings_count = await session.execute(select(DefaultSettings))
    if default_settings_count.first() is None:
        logger.warning("Настройки по умолчанию не найдены, создаем их")
        await create_initial_default_settings(session)
    
    # Получаем все активные настройки по умолчанию
    default_statuses = await session.execute(
        select(DefaultSettings).where(
            DefaultSettings.setting_type == "status",
            DefaultSettings.is_active == True
        )
    )
    default_priorities = await session.execute(
        select(DefaultSettings).where(
            DefaultSettings.setting_type == "priority",
            DefaultSettings.is_active == True
        )
    )
    default_durations = await session.execute(
        select(DefaultSettings).where(
            DefaultSettings.setting_type == "duration",
            DefaultSettings.is_active == True
        )
    )
    default_task_types = await session.execute(
        select(DefaultSettings).where(
            DefaultSettings.setting_type == "task_type",
            DefaultSettings.is_active == True
        )
    )
    
    # Создаем статусы для пользователя
    status_count = 0
    for default_status in default_statuses.scalars():
        status_data = json.loads(default_status.value)
        db_status = StatusSetting(
            user_id=user_id,
            name=status_data["name"],
            code=status_data["code"],
            color=status_data["color"],
            order=status_data["order"],
            is_default=status_data["is_default"],
            is_final=status_data["is_final"],
            is_active=status_data["is_active"]
        )
        session.add(db_status)
        status_count += 1
    
    # Создаем приоритеты для пользователя
    priority_count = 0
    for default_priority in default_priorities.scalars():
        priority_data = json.loads(default_priority.value)
        db_priority = PrioritySetting(
            user_id=user_id,
            name=priority_data["name"],
            color=priority_data["color"],
            order=priority_data["order"],
            is_default=priority_data["is_default"],
            is_active=priority_data["is_active"]
        )
        session.add(db_priority)
        priority_count += 1
    
    # Создаем продолжительности для пользователя
    duration_count = 0
    for default_duration in default_durations.scalars():
        duration_data = json.loads(default_duration.value)
        
        # Преобразуем строковое значение duration_type в объект перечисления DurationType
        duration_type_str = duration_data["duration_type"]
        duration_type = None
        
        # Ищем соответствующее значение в перечислении
        for dt in DurationType:
            if dt.value == duration_type_str:
                duration_type = dt
                break
        
        # Если не нашли, используем значение по умолчанию
        if duration_type is None:
            logger.warning(f"Неизвестный тип длительности: {duration_type_str}, используем DAYS")
            duration_type = DurationType.DAYS
        
        db_duration = DurationSetting(
            user_id=user_id,
            name=duration_data["name"],
            duration_type=duration_type,
            value=duration_data["value"],
            is_default=duration_data["is_default"],
            is_active=duration_data["is_active"]
        )
        session.add(db_duration)
        duration_count += 1

    # Создаем типы задач для пользователя
    task_type_count = 0
    for default_task_type in default_task_types.scalars():
        task_type_data = json.loads(default_task_type.value)
        db_task_type = TaskTypeSetting(
            user_id=user_id,
            name=task_type_data["name"],
            description=task_type_data["description"],
            color=task_type_data["color"],
            order=task_type_data["order"],
            is_default=task_type_data["is_default"],
            is_active=task_type_data["is_active"]
        )
        session.add(db_task_type)
        task_type_count += 1
    
    try:
        await session.commit()
        logger.debug(f"Созданы настройки для пользователя {user_id}: "
                    f"{status_count} статусов, {priority_count} приоритетов, "
                    f"{duration_count} длительностей, {task_type_count} типов задач")
    except Exception as e:
        logger.exception(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
        await session.rollback()
        raise 