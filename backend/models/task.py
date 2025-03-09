from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class TaskTypeSetting(Base):
    __tablename__ = "task_type_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("Task", back_populates="type")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    type_id = Column(Integer, ForeignKey("task_type_settings.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=True)
    priority_id = Column(Integer, ForeignKey("priorities.id"), nullable=True)
    duration_id = Column(Integer, ForeignKey("durations.id"), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    type = relationship("TaskTypeSetting", back_populates="tasks")
    status = relationship("Status", back_populates="tasks")
    priority = relationship("Priority", back_populates="tasks")
    duration = relationship("Duration", back_populates="tasks") 