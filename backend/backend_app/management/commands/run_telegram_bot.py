import logging
import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

#from telegram_django_bot.management.commands.run_telegram_bot import Command as TelegramBotCommand
#from telegram_django_bot.tg_dj_bot import TelegramDjangoBot
from telegram_django_bot.models import TelegramUser
#from telegram_django_bot.routing import MessageRouter, CallbackRouter

#from ../../models import Task, TaskType, TaskPriority, TaskDuration, Reminder

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, os.environ.get('LOGGER_LEVEL', 'INFO'))
)
logger = logging.getLogger(__name__)


class TaskPlannerBot(TelegramDjangoBot):
    """Расширение базового класса TelegramDjangoBot для планировщика задач"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Инициализация маршрутизаторов
        self.message_router = MessageRouter()
        self.callback_router = CallbackRouter()
        
        # Регистрация обработчиков сообщений
        self.message_router.register_message_handler(self.start_command, commands=['start'])
        self.message_router.register_message_handler(self.help_command, commands=['help'])
        self.message_router.register_message_handler(self.tasks_command, commands=['tasks'])
        self.message_router.register_message_handler(self.add_task_command, commands=['add_task'])
        self.message_router.register_message_handler(self.edit_types_command, commands=['edit_types'])
        self.message_router.register_message_handler(self.edit_priorities_command, commands=['edit_priorities'])
        
        # Регистрация обработчиков callback-запросов
        self.callback_router.register_callback_handler(self.task_callback, lambda c: c.data.startswith('task_'))
        self.callback_router.register_callback_handler(self.add_task_callback, lambda c: c.data.startswith('add_task_'))
        self.callback_router.register_callback_handler(self.edit_task_callback, lambda c: c.data.startswith('edit_task_'))
        self.callback_router.register_callback_handler(self.delete_task_callback, lambda c: c.data.startswith('delete_task_'))
        self.callback_router.register_callback_handler(self.complete_task_callback, lambda c: c.data.startswith('complete_task_'))
        self.callback_router.register_callback_handler(self.add_reminder_callback, lambda c: c.data.startswith('add_reminder_'))
        self.callback_router.register_callback_handler(self.type_callback, lambda c: c.data.startswith('type_'))
        self.callback_router.register_callback_handler(self.priority_callback, lambda c: c.data.startswith('priority_'))
        self.callback_router.register_callback_handler(self.duration_callback, lambda c: c.data.startswith('duration_'))
        
        # Инициализация состояний пользователей
        self.user_states = {}
    
    async def start_command(self, update, context):
        """Обработчик команды /start"""
        user = update.effective_user
        tg_user, created = await TelegramUser.objects.aget_or_create(
            user_id=user.id,
            defaults={
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        )
        
        # Создаем пользователя Django, если его еще нет
        if not tg_user.django_user:
            django_user = await User.objects.acreate(
                username=f"tg_{user.id}",
                first_name=user.first_name or "",
                last_name=user.last_name or ""
            )
            tg_user.django_user = django_user
            await tg_user.asave()
        
        # Создаем базовые типы задач, если их еще нет
        if not await TaskType.objects.aexists():
            await TaskType.objects.abulk_create([
                TaskType(name="Личные"),
                TaskType(name="Семейные"),
                TaskType(name="Рабочие")
            ])
        
        # Создаем базовые приоритеты задач, если их еще нет
        if not await TaskPriority.objects.aexists():
            await TaskPriority.objects.abulk_create([
                TaskPriority(name="Срочные и важные"),
                TaskPriority(name="Важные, но не срочные"),
                TaskPriority(name="Срочные, но не важные"),
                TaskPriority(name="Не срочные и не важные")
            ])
        
        # Создаем базовые продолжительности задач, если их еще нет
        if not await TaskDuration.objects.aexists():
            await TaskDuration.objects.abulk_create([
                TaskDuration(name="На день", days=1),
                TaskDuration(name="На неделю", days=7),
                TaskDuration(name="На месяц", days=30),
                TaskDuration(name="На год", days=365)
            ])
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Привет, {user.first_name}! Я бот для планирования задач. "
                 f"Используй /help, чтобы узнать, что я умею."
        )
    
    async def help_command(self, update, context):
        """Обработчик команды /help"""
        help_text = (
            "Я помогу тебе организовать твои задачи. Вот что я умею:\n\n"
            "/tasks - показать список твоих задач\n"
            "/add_task - добавить новую задачу\n"
            "/edit_types - редактировать типы задач\n"
            "/edit_priorities - редактировать приоритеты задач\n\n"
            "Ты можешь добавлять задачи разных типов (личные, рабочие, семейные и др.), "
            "устанавливать приоритеты (срочные-несрочные, важные-неважные) "
            "и продолжительность (на день, на месяц, на год).\n\n"
            "Также ты можешь настроить напоминания о задачах."
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text
        )
    
    async def tasks_command(self, update, context):
        """Обработчик команды /tasks - показывает список задач"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user = update.effective_user
        tg_user = await TelegramUser.objects.aget(user_id=user.id)
        
        # Получаем задачи пользователя
        tasks = Task.objects.filter(user=tg_user.django_user, completed=False).order_by('deadline')
        
        if not await tasks.aexists():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="У тебя пока нет активных задач. Используй /add_task, чтобы добавить новую задачу."
            )
            return
        
        # Получаем продолжительность "На день" (по умолчанию)
        default_duration = await TaskDuration.objects.aget(name="На день")
        
        # Фильтруем задачи по продолжительности (по умолчанию - на день)
        filtered_tasks = tasks.filter(duration=default_duration)
        
        if not await filtered_tasks.aexists():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="У тебя нет задач на день. Показываю все задачи."
            )
            filtered_tasks = tasks
        
        # Создаем клавиатуру для выбора продолжительности
        keyboard = [
            [
                InlineKeyboardButton("На день", callback_data="duration_day"),
                InlineKeyboardButton("На неделю", callback_data="duration_week"),
                InlineKeyboardButton("На месяц", callback_data="duration_month"),
                InlineKeyboardButton("На год", callback_data="duration_year"),
            ]
        ]
        
        # Добавляем кнопки для каждой задачи
        async for task in filtered_tasks:
            deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")
            task_type = await task.task_type.aget() if task.task_type else None
            priority = await task.priority.aget() if task.priority else None
            
            task_info = f"{task.title} - {deadline_str}"
            if task_type:
                task_info += f" - {task_type.name}"
            if priority:
                task_info += f" - {priority.name}"
            
            keyboard.append([InlineKeyboardButton(task_info, callback_data=f"task_{task.id}")])
        
        # Добавляем кнопку для добавления новой задачи
        keyboard.append([InlineKeyboardButton("➕ Добавить задачу", callback_data="add_task_start")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Твои задачи:",
            reply_markup=reply_markup
        )
    
    async def add_task_command(self, update, context):
        """Обработчик команды /add_task - начинает процесс добавления задачи"""
        user = update.effective_user
        self.user_states[user.id] = {"state": "add_task_title"}
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Введи название задачи:"
        )
    
    async def edit_types_command(self, update, context):
        """Обработчик команды /edit_types - редактирование типов задач"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Получаем все типы задач
        types = TaskType.objects.all()
        
        keyboard = []
        async for task_type in types:
            keyboard.append([
                InlineKeyboardButton(task_type.name, callback_data=f"type_{task_type.id}"),
                InlineKeyboardButton("❌", callback_data=f"delete_type_{task_type.id}")
            ])
        
        # Добавляем кнопку для добавления нового типа
        keyboard.append([InlineKeyboardButton("➕ Добавить тип", callback_data="add_type")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Типы задач:",
            reply_markup=reply_markup
        )
    
    async def edit_priorities_command(self, update, context):
        """Обработчик команды /edit_priorities - редактирование приоритетов задач"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Получаем все приоритеты задач
        priorities = TaskPriority.objects.all()
        
        keyboard = []
        async for priority in priorities:
            keyboard.append([
                InlineKeyboardButton(priority.name, callback_data=f"priority_{priority.id}"),
                InlineKeyboardButton("❌", callback_data=f"delete_priority_{priority.id}")
            ])
        
        # Добавляем кнопку для добавления нового приоритета
        keyboard.append([InlineKeyboardButton("➕ Добавить приоритет", callback_data="add_priority")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Приоритеты задач:",
            reply_markup=reply_markup
        )
    
    async def task_callback(self, update, context):
        """Обработчик нажатия на задачу"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        query = update.callback_query
        await query.answer()
        
        task_id = int(query.data.split('_')[1])
        task = await Task.objects.aget(id=task_id)
        
        task_type = await task.task_type.aget() if task.task_type else None
        priority = await task.priority.aget() if task.priority else None
        duration = await task.duration.aget() if task.duration else None
        
        task_info = (
            f"*{task.title}*\n\n"
            f"Описание: {task.description or 'Нет описания'}\n"
            f"Срок: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
            f"Тип: {task_type.name if task_type else 'Не указан'}\n"
            f"Приоритет: {priority.name if priority else 'Не указан'}\n"
            f"Продолжительность: {duration.name if duration else 'Не указана'}\n"
            f"Статус: {'Выполнено' if task.completed else 'Не выполнено'}"
        )
        
        # Создаем клавиатуру для действий с задачей
        keyboard = [
            [
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_task_{task.id}"),
                InlineKeyboardButton("✅ Выполнено", callback_data=f"complete_task_{task.id}")
            ],
            [
                InlineKeyboardButton("🔔 Добавить напоминание", callback_data=f"add_reminder_{task.id}"),
                InlineKeyboardButton("❌ Удалить", callback_data=f"delete_task_{task.id}")
            ],
            [InlineKeyboardButton("« Назад к списку", callback_data="tasks_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=task_info,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def add_task_callback(self, update, context):
        """Обработчик callback для добавления задачи"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "add_task_start":
            self.user_states[query.from_user.id] = {"state": "add_task_title"}
            await query.edit_message_text(
                text="Введи название задачи:"
            )
    
    async def edit_task_callback(self, update, context):
        """Обработчик callback для редактирования задачи"""
        query = update.callback_query
        await query.answer()
        
        task_id = int(query.data.split('_')[2])
        self.user_states[query.from_user.id] = {"state": "edit_task_title", "task_id": task_id}
        
        await query.edit_message_text(
            text="Введи новое название задачи (или отправь /skip, чтобы оставить без изменений):"
        )
    
    async def delete_task_callback(self, update, context):
        """Обработчик callback для удаления задачи"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        query = update.callback_query
        await query.answer()
        
        task_id = int(query.data.split('_')[2])
        task = await Task.objects.aget(id=task_id)
        
        # Создаем клавиатуру для подтверждения удаления
        keyboard = [
            [
                InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete_task_{task.id}"),
                InlineKeyboardButton("Нет, отмена", callback_data=f"task_{task.id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"Ты уверен, что хочешь удалить задачу '{task.title}'?",
            reply_markup=reply_markup
        )
    
    async def complete_task_callback(self, update, context):
        """Обработчик callback для отметки задачи как выполненной"""
        query = update.callback_query
        await query.answer()
        
        task_id = int(query.data.split('_')[2])
        task = await Task.objects.aget(id=task_id)
        
        task.completed = True
        task.completed_at = timezone.now()
        await task.asave()
        
        await query.edit_message_text(
            text=f"Задача '{task.title}' отмечена как выполненная! 🎉\n\nИспользуй /tasks, чтобы увидеть оставшиеся задачи."
        )
    
    async def add_reminder_callback(self, update, context):
        """Обработчик callback для добавления напоминания"""
        query = update.callback_query
        await query.answer()
        
        task_id = int(query.data.split('_')[2])
        self.user_states[query.from_user.id] = {"state": "add_reminder_date", "task_id": task_id}
        
        await query.edit_message_text(
            text="Введи дату и время напоминания в формате ДД.ММ.ГГГГ ЧЧ:ММ:"
        )
    
    async def type_callback(self, update, context):
        """Обработчик callback для типов задач"""
        # Здесь будет обработка выбора типа задачи
        pass
    
    async def priority_callback(self, update, context):
        """Обработчик callback для приоритетов задач"""
        # Здесь будет обработка выбора приоритета задачи
        pass
    
    async def duration_callback(self, update, context):
        """Обработчик callback для продолжительности задач"""
        # Здесь будет обработка выбора продолжительности задачи
        pass
    
    async def handle_message(self, update, context):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        
        # Если пользователь находится в процессе добавления или редактирования задачи
        if user_id in self.user_states:
            state = self.user_states[user_id]["state"]
            
            # Обработка добавления задачи
            if state == "add_task_title":
                self.user_states[user_id]["title"] = update.message.text
                self.user_states[user_id]["state"] = "add_task_description"
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Введи описание задачи (или отправь /skip, чтобы пропустить):"
                )
                return
            
            elif state == "add_task_description":
                if update.message.text == "/skip":
                    self.user_states[user_id]["description"] = None
                else:
                    self.user_states[user_id]["description"] = update.message.text
                
                self.user_states[user_id]["state"] = "add_task_deadline"
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Введи срок выполнения задачи в формате ДД.ММ.ГГГГ ЧЧ:ММ:"
                )
                return
            
            elif state == "add_task_deadline":
                try:
                    deadline = datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")
                    self.user_states[user_id]["deadline"] = timezone.make_aware(deadline)
                    
                    # Получаем типы задач для выбора
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    types = TaskType.objects.all()
                    
                    keyboard = []
                    async for task_type in types:
                        keyboard.append([InlineKeyboardButton(task_type.name, callback_data=f"select_type_{task_type.id}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    self.user_states[user_id]["state"] = "add_task_type"
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Выбери тип задачи:",
                        reply_markup=reply_markup
                    )
                except ValueError:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Неверный формат даты. Пожалуйста, введи дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:"
                    )
                return
            
            # Обработка добавления напоминания
            elif state == "add_reminder_date":
                try:
                    remind_at = datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")
                    remind_at = timezone.make_aware(remind_at)
                    
                    task_id = self.user_states[user_id]["task_id"]
                    task = await Task.objects.aget(id=task_id)
                    
                    # Создаем напоминание
                    reminder = Reminder(task=task, remind_at=remind_at)
                    await reminder.asave()
                    
                    del self.user_states[user_id]
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Напоминание о задаче '{task.title}' установлено на {remind_at.strftime('%d.%m.%Y %H:%M')}!"
                    )
                except ValueError:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Неверный формат даты. Пожалуйста, введи дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:"
                    )
                return
        
        # Если пользователь не находится в каком-либо процессе, обрабатываем сообщение как обычно
        await self.message_router.handle_message(update, context)


class Command(TelegramBotCommand):
    """Команда Django для запуска Telegram бота"""
    
    def handle(self, *args, **options):
        """Обработчик команды"""
        # Получаем токен из переменных окружения
        token = os.environ.get('TOKEN')
        if not token:
            self.stderr.write(self.style.ERROR('Токен не найден в переменных окружения'))
            return
        
        # Создаем и запускаем бота
        bot = TaskPlannerBot(token)
        bot.run()
