import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from backend.database import get_session, create_user_settings
from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.auth_service import AuthService
from backend.services.settings_service import SettingsService
from backend.dialogs.task_dialogs import TaskDialog


router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start, создает нового пользователя"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    logger.info(f"Команда /start от пользователя {user_id} ({username})")
    
    async with get_session() as session:
        auth_service = AuthService(session)
        # Проверяем, существует ли пользователь
        user = await auth_service.get_user_by_id(str(user_id))
        
        if not user:
            # Создаем нового пользователя
            logger.info(f"Создаем нового пользователя {user_id} ({username})")
            user = await auth_service.create_user(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            # Создаем настройки для нового пользователя
            try:
                await create_user_settings(user.telegram_id, session)
                logger.info(f"Настройки для пользователя {user_id} созданы успешно")
            except Exception as e:
                logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
            
            logger.info(f"Создан новый пользователь: {user_id} ({username})")
        else:
            logger.info(f"Пользователь {user_id} уже существует")
            # Проверяем, есть ли у пользователя настройки
            settings_service = SettingsService(session)
            statuses = await settings_service.get_statuses(str(user_id))
            if not statuses:
                logger.info(f"У пользователя {user_id} нет настроек, создаем их")
                try:
                    await create_user_settings(user.telegram_id, session)
                    logger.info(f"Настройки для пользователя {user_id} созданы успешно")
                except Exception as e:
                    logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
        
    await message.answer(i18n.format_value("started"))


@router.message(Command("stop"))
async def stop_command(message: Message):
    await message.answer(i18n.format_value("stopped"))

@router.message(Command("tasks"))
async def list_tasks(message: Message):
    """Показать список задач"""
    async with get_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.get_tasks(str(message.from_user.id))
        
        if not tasks:
            await message.answer(i18n.format_value("tasks-empty"))
            return

        response = i18n.format_value("tasks-header") + "\n\n"
        for task in tasks:
            status_emoji = "✅" if task['status'] and task['status']['code'] == 'completed' else "⏳"
            priority_emoji = "🔴" if task['priority'] and task['priority']['name'].lower() == 'высокий' else "🟡" if task['priority'] and task['priority']['name'].lower() == 'средний' else "🟢"
            
            response += i18n.format_value("task-item", {
                "status_emoji": status_emoji,
                "priority_emoji": priority_emoji,
                "id": task['id'],
                "title": task['title']
            }) + "\n"
            
            if task['description']:
                response += i18n.format_value("task-description-line", {
                    "description": task['description']
                }) + "\n"
                
            if task['deadline']:
                response += i18n.format_value("task-deadline-line", {
                    "deadline": task['deadline']
                }) + "\n"
                
            response += "\n"

        await message.answer(response)

@router.message(Command("add_task"))
async def start_add_task(message: Message, dialog_manager: DialogManager):
    """Начать процесс создания новой задачи"""
    await dialog_manager.start(TaskDialog.title, mode=StartMode.NORMAL)

@router.message(Command("delete_task"))
async def delete_task(message: Message):
    """Удалить задачу"""
    try:
        task_id = int(message.text.split()[1])
        async with get_session() as session:
            task_service = TaskService(session)
            success = await task_service.delete_task(str(message.from_user.id), task_id)
            
            if success:
                await message.answer(i18n.format_value("task-deleted", {"id": task_id}))
            else:
                await message.answer(i18n.format_value("task-delete-error", {"id": task_id}))
    except (IndexError, ValueError):
        await message.answer(i18n.format_value("task-delete-usage"))

@router.message(Command("help"))
async def show_help(message: Message):
    """Показать справку по командам"""
    help_text = (
        i18n.format_value("help-header") + "\n\n" +
        i18n.format_value("help-tasks") + "\n" +
        i18n.format_value("help-add-task") + "\n" +
        i18n.format_value("help-delete-task") + "\n" +
        "\n" +
        i18n.format_value("settings_command_help") + "\n" +
        i18n.format_value("settings_statuses_command_help") + "\n" +
        i18n.format_value("settings_priorities_command_help") + "\n" +
        i18n.format_value("settings_durations_command_help") + "\n" +
        i18n.format_value("settings_task_types_command_help") + "\n" +
        i18n.format_value("create_settings_command_help") + "\n" +
        "\n" +
        i18n.format_value("help-help")
    )
    await message.answer(help_text)

@router.message(Command("settings"))
async def show_settings(message: Message):
    """Показать меню настроек пользователя"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=i18n.format_value("settings_statuses"),
            callback_data="settings_statuses"
        )],
        [InlineKeyboardButton(
            text=i18n.format_value("settings_priorities"),
            callback_data="settings_priorities"
        )],
        [InlineKeyboardButton(
            text=i18n.format_value("settings_durations"),
            callback_data="settings_durations"
        )],
        [InlineKeyboardButton(
            text=i18n.format_value("settings_task_types"),
            callback_data="settings_task_types"
        )]
    ])
    
    await message.answer(
        i18n.format_value("settings_header"),
        reply_markup=keyboard
    )

@router.callback_query(F.data == "settings_statuses")
async def on_settings_statuses_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку настроек статусов"""
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    logger.info(f"Обработка колбэка settings_statuses от пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(str(user_id))
        
        logger.info(f"Получено {len(statuses) if statuses else 0} статусов для пользователя {user_id}")
        
        if not statuses:
            logger.warning(f"Статусы для пользователя {user_id} не найдены")
            await callback_query.message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_statuses") + "\n\n"
        for status in statuses:
            logger.debug(f"Статус: {status}")
            response += f"• {status['name']} ({status['code']})\n"
            response += f"  Цвет: {status['color']}\n"
            response += f"  По умолчанию: {'✅' if status['is_default'] else '❌'}\n"
            response += f"  Финальный: {'✅' if status['is_final'] else '❌'}\n\n"
            
        await callback_query.message.answer(response)

@router.callback_query(F.data == "settings_priorities")
async def on_settings_priorities_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку настроек приоритетов"""
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    logger.info(f"Обработка колбэка settings_priorities от пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        priorities = await settings_service.get_priorities(str(user_id))
        
        if not priorities:
            await callback_query.message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_priorities") + "\n\n"
        for priority in priorities:
            response += f"• {priority['name']}\n"
            response += f"  Цвет: {priority['color']}\n"
            response += f"  По умолчанию: {'✅' if priority['is_default'] else '❌'}\n\n"
            
        await callback_query.message.answer(response)

@router.callback_query(F.data == "settings_durations")
async def on_settings_durations_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку настроек длительностей"""
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    logger.info(f"Обработка колбэка settings_durations от пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        durations = await settings_service.get_durations(str(user_id))
        
        if not durations:
            await callback_query.message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_durations") + "\n\n"
        for duration in durations:
            try:
                response += f"• {duration['name']}\n"
                if 'duration_type' in duration:
                    response += f"  Тип: {duration['duration_type']}\n"
                elif 'type' in duration:
                    response += f"  Тип: {duration['type']}\n"
                response += f"  Значение: {duration['value']}\n"
                response += f"  По умолчанию: {'✅' if duration['is_default'] else '❌'}\n\n"
            except Exception as e:
                logger.error(f"Ошибка при обработке длительности: {e}")
                logger.error(f"Данные длительности: {duration}")
            
        await callback_query.message.answer(response)

@router.callback_query(F.data == "settings_task_types")
async def on_settings_task_types_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку настроек типов задач"""
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    logger.info(f"Обработка колбэка settings_task_types от пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_types = await settings_service.get_task_types(str(user_id))
        
        if not task_types:
            await callback_query.message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_task_types") + "\n\n"
        for task_type in task_types:
            response += f"• {task_type['name']}\n"
            if task_type.get('description'):
                response += f"  Описание: {task_type['description']}\n"
            response += f"  Цвет: {task_type['color']}\n"
            response += f"  По умолчанию: {'✅' if task_type['is_default'] else '❌'}\n\n"
            
        await callback_query.message.answer(response)

@router.message(Command("create_settings"))
async def create_settings_command(message: Message):
    """Принудительно создает настройки для пользователя"""
    user_id = message.from_user.id
    logger.info(f"Команда /create_settings от пользователя {user_id}")
    
    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.get_user_by_id(str(user_id))
        
        if not user:
            await message.answer("Пользователь не найден. Сначала выполните команду /start")
            return
        
        try:
            # Принудительно создаем настройки для пользователя
            await create_user_settings(user.telegram_id, session)
            logger.info(f"Настройки для пользователя {user_id} созданы успешно")
            await message.answer("Настройки успешно созданы!")
        except Exception as e:
            logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
            await message.answer(f"Ошибка при создании настроек: {e}")

@router.message(Command("settings_statuses"))
async def show_statuses_settings(message: Message):
    """Показать настройки статусов задач"""
    user_id = message.from_user.id
    logger.info(f"Запрос настроек статусов для пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(str(user_id))
        
        logger.info(f"Получено {len(statuses) if statuses else 0} статусов для пользователя {user_id}")
        
        if not statuses:
            logger.warning(f"Статусы для пользователя {user_id} не найдены")
            await message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_statuses") + "\n\n"
        for status in statuses:
            logger.debug(f"Статус: {status}")
            response += f"• {status['name']} ({status['code']})\n"
            response += f"  Цвет: {status['color']}\n"
            response += f"  По умолчанию: {'✅' if status['is_default'] else '❌'}\n"
            response += f"  Финальный: {'✅' if status['is_final'] else '❌'}\n\n"
            
        await message.answer(response)

@router.message(Command("settings_priorities"))
async def show_priorities_settings(message: Message):
    """Показать настройки приоритетов задач"""
    user_id = message.from_user.id
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        priorities = await settings_service.get_priorities(str(user_id))
        
        if not priorities:
            await message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_priorities") + "\n\n"
        for priority in priorities:
            response += f"• {priority['name']}\n"
            response += f"  Цвет: {priority['color']}\n"
            response += f"  По умолчанию: {'✅' if priority['is_default'] else '❌'}\n\n"
            
        await message.answer(response)

@router.message(Command("settings_durations"))
async def show_durations_settings(message: Message):
    """Показать настройки длительностей задач"""
    user_id = message.from_user.id
    logger.info(f"Запрос настроек длительностей для пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        durations = await settings_service.get_durations(str(user_id))
        
        logger.info(f"Получено {len(durations) if durations else 0} длительностей для пользователя {user_id}")
        
        if not durations:
            logger.warning(f"Длительности для пользователя {user_id} не найдены")
            await message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_durations") + "\n\n"
        for duration in durations:
            try:
                response += f"• {duration['name']}\n"
                if 'duration_type' in duration:
                    response += f"  Тип: {duration['duration_type']}\n"
                elif 'type' in duration:
                    response += f"  Тип: {duration['type']}\n"
                response += f"  Значение: {duration['value']}\n"
                response += f"  По умолчанию: {'✅' if duration['is_default'] else '❌'}\n\n"
            except Exception as e:
                logger.error(f"Ошибка при обработке длительности: {e}")
                logger.error(f"Данные длительности: {duration}")
            
        await message.answer(response)

@router.message(Command("settings_types"))
async def show_task_types_settings(message: Message):
    """Показать настройки типов задач"""
    user_id = message.from_user.id
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_types = await settings_service.get_task_types(str(user_id))
        
        if not task_types:
            await message.answer(i18n.format_value("settings_not_found"))
            return
            
        response = i18n.format_value("settings_task_types") + "\n\n"
        for task_type in task_types:
            response += f"• {task_type['name']}\n"
            if task_type.get('description'):
                response += f"  Описание: {task_type['description']}\n"
            response += f"  Цвет: {task_type['color']}\n"
            response += f"  По умолчанию: {'✅' if task_type['is_default'] else '❌'}\n\n"
            
        await message.answer(response) 