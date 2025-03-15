from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum, JSON, Text, BigInteger
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()
metadata = Base.metadata

class DurationType(enum.Enum):
    """Типы продолжительности"""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"
    
    @classmethod
    def _missing_(cls, value:str):
        """Обработка отсутствующих значений перечисления"""
        # Проверяем, есть ли значение в нижнем регистре
        for member in cls:
            if member.value == value:
                return member
        
        # Проверяем, есть ли значение в верхнем регистре
        for member in cls:
            if member.name == value or member.name == value.upper():
                return member
        
        # Если ничего не найдено, возвращаем None
        return None

class GlobalSettings(Base):
    """Глобальные настройки приложения"""
    __tablename__ = 'global_settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)  # Ключ настройки
    value = Column(Text)  # Значение настройки
    description = Column(String(255))  # Описание настройки
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class DefaultSettings(Base):
    """Настройки по умолчанию для новых пользователей"""
    __tablename__ = 'default_settings'

    id = Column(Integer, primary_key=True)
    setting_type = Column(String(50), nullable=False)  # Тип настройки: status, priority, duration
    name = Column(String(100), nullable=False)  # Название настройки
    value = Column(Text, nullable=False)  # Значение настройки в JSON
    is_active = Column(Boolean, default=True)  # Активна ли настройка
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=func.now())
    settings = Column(JSON, default=dict)  # Пользовательские настройки в JSON

    # Связи с другими таблицами
    tasks = relationship('Task', back_populates='user')
    priority_settings = relationship('PrioritySetting', back_populates='user')
    duration_settings = relationship('DurationSetting', back_populates='user')
    status_settings = relationship('StatusSetting', back_populates='user')
    task_type_settings = relationship('TaskTypeSetting', back_populates='user')

class StatusSetting(Base):
    """Настройки статусов задач для пользователя"""
    __tablename__ = 'status_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)  # Название статуса
    code = Column(String(50), nullable=False)  # Код статуса для программной обработки
    color = Column(String(7))  # HEX код цвета для отображения
    order = Column(Integer, default=0)  # Порядок сортировки
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Статус по умолчанию для новых задач
    is_final = Column(Boolean, default=False)  # Является ли статус финальным (например, "выполнено", "отменено")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Связи
    user = relationship('User', back_populates='status_settings')
    tasks = relationship('Task', back_populates='status')

class PrioritySetting(Base):
    """Настройки приоритетов для пользователя"""
    __tablename__ = 'priority_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)  # Название приоритета
    color = Column(String(7))  # HEX код цвета для отображения
    order = Column(Integer, default=0)  # Порядок сортировки
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Приоритет по умолчанию для новых задач
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Связи
    user = relationship('User', back_populates='priority_settings')
    tasks = relationship('Task', back_populates='priority')

class DurationSetting(Base):
    """Настройки продолжительности для пользователя"""
    __tablename__ = 'duration_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)  # Название (день, месяц, год)
    duration_type = Column(Enum(DurationType), nullable=False, default=DurationType.DAYS)  # Тип продолжительности
    value = Column(Integer, nullable=False)  # Значение (количество дней, месяцев, лет)
    is_default = Column(Boolean, default=False)  # Является ли значением по умолчанию
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Связи
    user = relationship('User', back_populates='duration_settings')
    tasks = relationship('Task', back_populates='duration')

    async def calculate_deadline_async(self, session, from_date=None):
        """Рассчитать дедлайн на основе продолжительности (асинхронный метод)"""
        if from_date is None:
            # Используем текущую дату и время
            from_date = datetime.now()
        elif isinstance(from_date, date) and not isinstance(from_date, datetime):
            # Если передана только дата (без времени), добавляем текущее время
            now = datetime.now()
            from_date = datetime.combine(from_date, now.time())

        # Получаем актуальные значения из базы данных
        duration = await session.get(DurationSetting, self.id)
        if not duration:
            return from_date

        if duration.duration_type == DurationType.DAYS:
            return from_date + timedelta(days=duration.value)
        elif duration.duration_type == DurationType.WEEKS:
            return from_date + timedelta(weeks=duration.value)
        elif duration.duration_type == DurationType.MONTHS:
            return from_date + relativedelta(months=duration.value)
        elif duration.duration_type == DurationType.YEARS:
            return from_date + relativedelta(years=duration.value)

        return from_date

class Task(Base):
    """Модель задачи"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(1000))

    # Связи с настройками
    status_id = Column(Integer, ForeignKey('status_settings.id', ondelete='SET NULL'))
    priority_id = Column(Integer, ForeignKey('priority_settings.id', ondelete='SET NULL'))
    type_id = Column(Integer, ForeignKey("task_type_settings.id"), nullable=True)
    duration_id = Column(Integer, ForeignKey('duration_settings.id', ondelete='SET NULL'))

    # Даты
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deadline = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Напоминания
    reminders = Column(JSON, default=list)  # Список дат напоминаний в формате ISO
    last_reminder_sent = Column(DateTime(timezone=True))

    # Дополнительные поля
    tags = Column(JSON, default=list)  # Теги для группировки задач
    custom_fields = Column(JSON, default=dict)  # Пользовательские поля

    # Связи
    user = relationship('User', back_populates='tasks')
    status = relationship('StatusSetting', back_populates='tasks')
    priority = relationship('PrioritySetting', back_populates='tasks')
    type = relationship("TaskTypeSetting", back_populates="tasks")
    duration = relationship('DurationSetting', back_populates='tasks')

    def add_reminder(self, reminder_date: datetime):
        """Добавить напоминание"""
        if not self.reminders:
            self.reminders = []
        self.reminders.append(reminder_date.isoformat())
        self.reminders.sort()

    def remove_reminder(self, reminder_date: datetime):
        """Удалить напоминание"""
        if self.reminders:
            self.reminders = [r for r in self.reminders if r != reminder_date.isoformat()]

    def get_next_reminder(self) -> datetime | None:
        """Получить следующее напоминание"""
        if not self.reminders:
            return None
        now = datetime.now()
        future_reminders = [
            datetime.fromisoformat(r) for r in self.reminders
            if datetime.fromisoformat(r) > now
        ]
        return min(future_reminders) if future_reminders else None

    def change_status(self, new_status: StatusSetting):
        """Изменить статус задачи"""
        self.status = new_status
        if new_status.is_final:
            self.completed_at = datetime.now()
        else:
            self.completed_at = None

    def is_overdue(self) -> bool:
        """Проверить, просрочена ли задача"""
        if not self.deadline or self.completed_at or (self.status and self.status.is_final):
            return False
        return datetime.now() > self.deadline


class TaskTypeSetting(Base):
    __tablename__ = "task_type_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    tasks = relationship("Task", back_populates="type")
    user = relationship('User', back_populates='task_type_settings')
