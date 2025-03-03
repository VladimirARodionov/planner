from django.db import models
from django.utils import timezone
from telegram_django_bot.models import TelegramUser


class User(TelegramUser):
    pass

class TaskType(models.Model):
    id = models.BigIntegerField(primary_key=True)
    """Тип задачи: личные, семейные, рабочие и т.д."""
    name = models.CharField(max_length=100, verbose_name="Название типа")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Тип задачи"
        verbose_name_plural = "Типы задач"


class TaskPriority(models.Model):
    id = models.BigIntegerField(primary_key=True)
    """Приоритет задачи: срочные-несрочные, важные-неважные"""
    name = models.CharField(max_length=100, verbose_name="Название приоритета")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Приоритет задачи"
        verbose_name_plural = "Приоритеты задач"


class TaskDuration(models.Model):
    id = models.BigIntegerField(primary_key=True)
    """Продолжительность задачи: на день, на месяц, на год"""
    name = models.CharField(max_length=100, verbose_name="Название продолжительности")
    days = models.IntegerField(verbose_name="Количество дней", default=1)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Продолжительность задачи"
        verbose_name_plural = "Продолжительности задач"


class Task(models.Model):
    id = models.BigIntegerField(primary_key=True)
    """Модель задачи"""
    title = models.CharField(max_length=255, verbose_name="Название задачи")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    deadline = models.DateTimeField(verbose_name="Срок выполнения")
    completed = models.BooleanField(default=False, verbose_name="Выполнено")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    
    # Связи с другими моделями
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks", verbose_name="Пользователь")
    task_type = models.ForeignKey(TaskType, on_delete=models.SET_NULL, null=True, related_name="tasks", verbose_name="Тип задачи")
    priority = models.ForeignKey(TaskPriority, on_delete=models.SET_NULL, null=True, related_name="tasks", verbose_name="Приоритет")
    duration = models.ForeignKey(TaskDuration, on_delete=models.SET_NULL, null=True, related_name="tasks", verbose_name="Продолжительность")
    
    def complete(self):
        """Отметить задачу как выполненную"""
        self.completed = True
        self.completed_at = timezone.now()
        self.save()
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-created_at']


class Reminder(models.Model):
    id = models.BigIntegerField(primary_key=True)
    """Модель напоминания о задаче"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reminders", verbose_name="Задача")
    remind_at = models.DateTimeField(verbose_name="Время напоминания")
    sent = models.BooleanField(default=False, verbose_name="Отправлено")
    
    def __str__(self):
        return f"Напоминание о {self.task.title} в {self.remind_at}"
    
    class Meta:
        verbose_name = "Напоминание"
        verbose_name_plural = "Напоминания"
        ordering = ['remind_at']
