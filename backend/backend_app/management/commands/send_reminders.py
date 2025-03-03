import logging
import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from telegram import Bot
from telegram.error import TelegramError

from telegram_django_bot.models import TelegramUser

from backend.backend_app.models import Reminder

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, os.environ.get('LOGGER_LEVEL', 'INFO'))
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Команда Django для отправки напоминаний о задачах"""
    
    help = 'Отправляет напоминания о задачах пользователям через Telegram'
    
    def handle(self, *args, **options):
        """Обработчик команды"""
        # Получаем токен из переменных окружения
        token = os.environ.get('TOKEN')
        if not token:
            self.stderr.write(self.style.ERROR('Токен не найден в переменных окружения'))
            return
        
        # Создаем экземпляр бота
        bot = Bot(token=token)
        
        # Получаем текущее время
        now = timezone.now()
        
        # Получаем напоминания, которые нужно отправить
        # (время напоминания прошло, но напоминание еще не отправлено)
        reminders = Reminder.objects.filter(
            remind_at__lte=now,
            sent=False
        ).select_related('task', 'task__user')
        
        self.stdout.write(f"Найдено {reminders.count()} напоминаний для отправки")
        
        # Отправляем напоминания
        for reminder in reminders:
            task = reminder.task
            user = task.user
            
            try:
                # Получаем Telegram ID пользователя
                tg_user = TelegramUser.objects.get(django_user=user)
                
                # Формируем текст напоминания
                reminder_text = (
                    f"🔔 *Напоминание о задаче*\n\n"
                    f"*{task.title}*\n"
                    f"Срок: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Описание: {task.description or 'Нет описания'}"
                )
                
                # Отправляем сообщение
                bot.send_message(
                    chat_id=tg_user.user_id,
                    text=reminder_text,
                    parse_mode='Markdown'
                )
                
                # Отмечаем напоминание как отправленное
                reminder.sent = True
                reminder.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Напоминание о задаче '{task.title}' отправлено пользователю {user.username}"
                ))
                
            except TelegramUser.DoesNotExist:
                self.stderr.write(self.style.ERROR(
                    f"Не найден Telegram пользователь для Django пользователя {user.username}"
                ))
            except TelegramError as e:
                self.stderr.write(self.style.ERROR(
                    f"Ошибка при отправке напоминания: {e}"
                ))
        
        self.stdout.write(self.style.SUCCESS("Отправка напоминаний завершена")) 