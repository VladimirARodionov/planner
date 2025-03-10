import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window, Data
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Button, Select, Back, Next, Row
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog import DialogManager
from typing import Any
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.widget_event import SimpleEventProcessor

from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService
from backend.database import get_session

logger = logging.getLogger(__name__)

class TaskDialog(StatesGroup):
    title = State()
    description = State()
    type = State()
    status = State()
    priority = State()
    duration = State()
    confirm = State()  # Новый шаг для подтверждения создания задачи

async def get_task_types(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"task_types": settings["task_types"]}

async def get_statuses(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"statuses": settings["statuses"]}

async def get_priorities(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"priorities": settings["priorities"]}

async def get_durations(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"durations": settings["durations"]}

async def on_task_created(event, widget, manager: DialogManager):
    # Закрываем диалог с передачей данных в результат
    logger.info("on_task_created called, dialog data: %s", manager.dialog_data)
    try:
        await main_process_result(start_data = None, result=manager.dialog_data, dialog_manager=manager)
        await manager.done(result=manager.dialog_data)
        logger.info("Dialog closed successfully with result")
    except Exception as e:
        logger.error(f"Error closing dialog: {e}")

async def on_title_success(event: Message, source: Any, manager: DialogManager, *args, **kwargs):
    if event.text and event.text.strip():
        manager.dialog_data["title"] = event.text.strip()
    else:
        manager.dialog_data["title"] = "Новая задача"
    await manager.next()

async def on_description_success(event: Message, source: Any, manager: DialogManager, *args, **kwargs):
    manager.dialog_data["description"] = None if event.text == '-' else event.text
    await manager.next()

async def on_type_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["type_id"] = item_id
    await manager.next()

async def on_status_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["status_id"] = item_id
    await manager.next()

async def on_priority_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["priority_id"] = item_id
    await manager.next()

async def on_duration_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["duration_id"] = item_id
    # Переходим к шагу подтверждения
    await manager.next()

async def get_task_summary(dialog_manager: DialogManager, **kwargs):
    """Получить сводку о создаваемой задаче"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        
        # Получаем данные о выбранных параметрах
        task_data = dialog_manager.dialog_data
        
        # Находим названия выбранных параметров
        type_name = "Не выбран"
        status_name = "Не выбран"
        priority_name = "Не выбран"
        duration_name = "Не выбрана"
        
        if task_data.get("type_id"):
            for task_type in settings["task_types"]:
                if task_type["id"] == task_data["type_id"]:
                    type_name = task_type["name"]
                    break
                    
        if task_data.get("status_id"):
            for status in settings["statuses"]:
                if status["id"] == task_data["status_id"]:
                    status_name = status["name"]
                    break
                    
        if task_data.get("priority_id"):
            for priority in settings["priorities"]:
                if priority["id"] == task_data["priority_id"]:
                    priority_name = priority["name"]
                    break
                    
        if task_data.get("duration_id"):
            for duration in settings["durations"]:
                if duration["id"] == task_data["duration_id"]:
                    duration_name = duration["name"]
                    break
        
        return {
            "title": task_data.get("title", "Новая задача"),
            "description": task_data.get("description", "Нет описания"),
            "type_name": type_name,
            "status_name": status_name,
            "priority_name": priority_name,
            "duration_name": duration_name
        }

async def main_process_result(start_data: Data, result: Any,
                              dialog_manager: DialogManager):
    logger.info("main_process_result called!")
    print("We have result:", result)
    logger.info("Start data: %s", start_data)
    logger.info("Result: %s", result)
    logger.info("Dialog data: %s", dialog_manager.dialog_data)
    
    # Создаем задачу при завершении диалога
    if result:
        try:
            async with get_session() as session:
                task_service = TaskService(session)
                user_id = str(dialog_manager.event.from_user.id)
                task = await task_service.create_task(
                    user_id,
                    result
                )
                
                if task:
                    task_type = task['type']['name'] if task['type'] else i18n.format_value("type-not-set")
                    status = task['status']['name'] if task['status'] else i18n.format_value("status-not-set")
                    priority = task['priority']['name'] if task['priority'] else i18n.format_value("priority-not-set")
                    duration = task['duration']['name'] if task['duration'] else i18n.format_value("duration-not-set")
                    deadline = task['deadline'] if task['deadline'] else i18n.format_value("deadline-not-set")
                    
                    await dialog_manager.event.answer(
                        i18n.format_value("task-created") + "\n\n" +
                        i18n.format_value("task-created-details", {
                            "title": task['title'],
                            "description": task['description'] or i18n.format_value("description-not-set"),
                            "type": task_type,
                            "status": status,
                            "priority": priority,
                            "duration": duration,
                            "deadline": deadline
                        })
                    )
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            await dialog_manager.event.answer(i18n.format_value("error"))


task_dialog = Dialog(
    Window(
        Const(i18n.format_value("task-title")),
        TextInput(id="title", on_success=SimpleEventProcessor(on_title_success)),
        Next(Const(i18n.format_value("next"))),
        state=TaskDialog.title,
    ),
    Window(
        Const(i18n.format_value("task-description")),
        TextInput(id="description", on_success=SimpleEventProcessor(on_description_success)),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.description,
    ),
    Window(
        Format(i18n.format_value("task-type")),
        Select(
            Format("{item[name]}"),
            id="type",
            item_id_getter=lambda x: x["id"],
            items="task_types",
            on_click=on_type_selected,
        ),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.type,
        getter=get_task_types,
    ),
    Window(
        Format(i18n.format_value("task-status")),
        Select(
            Format("{item[name]}"),
            id="status",
            item_id_getter=lambda x: x["id"],
            items="statuses",
            on_click=on_status_selected,
        ),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.status,
        getter=get_statuses,
    ),
    Window(
        Format(i18n.format_value("task-priority")),
        Select(
            Format("{item[name]}"),
            id="priority",
            item_id_getter=lambda x: x["id"],
            items="priorities",
            on_click=on_priority_selected,
        ),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.priority,
        getter=get_priorities,
    ),
    Window(
        Format(i18n.format_value("task-duration")),
        Select(
            Format("{item[name]}"),
            id="duration",
            item_id_getter=lambda x: x["id"],
            items="durations",
            on_click=on_duration_selected,
        ),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.duration,
        getter=get_durations,
    ),
    Window(
        Format(i18n.format_value("task-confirm-header")),
        Format(i18n.format_value("task-confirm-details", {
            "title": "{title}",
            "description": "{description}",
            "type": "{type_name}",
            "status": "{status_name}",
            "priority": "{priority_name}",
            "duration": "{duration_name}"
        })),
        Row(
            Back(Const(i18n.format_value("back"))),
            Button(Const(i18n.format_value("create")), id="create", on_click=on_task_created),
        ),
        state=TaskDialog.confirm,
        getter=get_task_summary,
    ),
    on_process_result=main_process_result
) 