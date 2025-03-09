import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode

from backend.database import get_session
from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.dialogs.task_dialogs import task_dialog, TaskDialog


router = Router()
logger = logging.getLogger(__name__)

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
        i18n.format_value("help-help")
    )
    await message.answer(help_text) 