from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import json

from backend.create_bot import db_string
from backend.db.models import DurationType

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем асинхронный движок SQLAlchemy

engine = create_async_engine(db_string, echo=True)

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
    from backend.db.models import DefaultSettings, GlobalSettings
    
    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    
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
    from backend.db.models import GlobalSettings
    
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
    from backend.db.models import DefaultSettings
    
    # Создаем стандартные статусы
    default_statuses = [
        {
            "name": "Ожидает выполнения",
            "code": "pending",
            "color": "#808080",  # Серый
            "order": 1,
            "is_default": True,
            "is_final": False,
            "is_active": True
        },
        {
            "name": "В процессе",
            "code": "in_progress",
            "color": "#FFA500",  # Оранжевый
            "order": 2,
            "is_default": False,
            "is_final": False,
            "is_active": True
        },
        {
            "name": "На проверке",
            "code": "review",
            "color": "#4169E1",  # Синий
            "order": 3,
            "is_default": False,
            "is_final": False,
            "is_active": True
        },
        {
            "name": "Выполнено",
            "code": "completed",
            "color": "#008000",  # Зеленый
            "order": 4,
            "is_default": False,
            "is_final": True,
            "is_active": True
        },
        {
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
            "name": "Срочно и важно",
            "color": "#FF0000",
            "order": 1,
            "is_default": True,
            "is_active": True
        },
        {
            "name": "Важно, не срочно",
            "color": "#FFA500",
            "order": 2,
            "is_default": False,
            "is_active": True
        },
        {
            "name": "Срочно, не важно",
            "color": "#FFFF00",
            "order": 3,
            "is_default": False,
            "is_active": True
        },
        {
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
            "name": "На день",
            "duration_type": DurationType.DAYS.value,
            "value": 1,
            "is_default": True,
            "is_active": True
        },
        {
            "name": "На неделю",
            "duration_type": DurationType.WEEKS.value,
            "value": 1,
            "is_default": False,
            "is_active": True
        },
        {
            "name": "На месяц",
            "duration_type": DurationType.MONTHS.value,
            "value": 1,
            "is_default": False,
            "is_active": True
        },
        {
            "name": "На год",
            "duration_type": DurationType.YEARS.value,
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
    
    await session.commit()

# Функция для создания настроек пользователя на основе настроек по умолчанию
async def create_user_settings(user_id: int, session: AsyncSession):
    from backend.db.models import DefaultSettings, StatusSetting, PrioritySetting, DurationSetting
    
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
    
    # Создаем статусы для пользователя
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
    
    # Создаем приоритеты для пользователя
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
    
    # Создаем продолжительности для пользователя
    for default_duration in default_durations.scalars():
        duration_data = json.loads(default_duration.value)
        db_duration = DurationSetting(
            user_id=user_id,
            name=duration_data["name"],
            duration_type=duration_data["duration_type"],
            value=duration_data["value"],
            is_default=duration_data["is_default"],
            is_active=duration_data["is_active"]
        )
        session.add(db_duration)
    
    await session.commit() 