import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window, Data
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Button, Select, Back, Next, Row, Group
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
    logger.debug("on_task_created called, dialog data: %s", manager.dialog_data)
    try:
        # Вызываем main_process_result напрямую
        await main_process_result(start_data=None, result=manager.dialog_data, dialog_manager=manager)
        # Закрываем диалог без результата, чтобы не вызывать main_process_result второй раз
        await manager.done()
        logger.debug("Dialog closed successfully")
    except Exception as e:
        logger.exception(f"Error in on_task_created: {e}")

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
    logger.debug(f"on_type_selected called with item_id: {item_id}, type: {type(item_id)}")
    manager.dialog_data["type_id"] = str(item_id)
    logger.debug(f"Selected type_id: {item_id}, dialog_data: {manager.dialog_data}")
    await manager.next()

async def on_status_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    logger.debug(f"on_status_selected called with item_id: {item_id}, type: {type(item_id)}")
    manager.dialog_data["status_id"] = str(item_id)
    logger.debug(f"Selected status_id: {item_id}, dialog_data: {manager.dialog_data}")
    await manager.next()

async def on_priority_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    logger.debug(f"on_priority_selected called with item_id: {item_id}, type: {type(item_id)}")
    manager.dialog_data["priority_id"] = str(item_id)
    logger.debug(f"Selected priority_id: {item_id}, dialog_data: {manager.dialog_data}")
    await manager.next()

async def on_duration_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    logger.debug(f"on_duration_selected called with item_id: {item_id}, type: {type(item_id)}")
    manager.dialog_data["duration_id"] = str(item_id)
    logger.debug(f"Selected duration_id: {item_id}, dialog_data: {manager.dialog_data}")
    # Переходим к шагу подтверждения
    await manager.next()

async def get_task_summary(dialog_manager: DialogManager, **kwargs):
    """Получить сводку о создаваемой задаче"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    logger.debug(f"get_task_summary called, user_id: {user_id}, dialog_data: {dialog_manager.dialog_data}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        logger.debug(f"Settings: {settings}")
        
        # Получаем данные о выбранных параметрах
        task_data = dialog_manager.dialog_data
        logger.debug(f"Task data: {task_data}")
        
        # Выводим типы данных ID
        if task_data.get("type_id"):
            logger.debug(f"type_id: {task_data['type_id']}, type: {type(task_data['type_id'])}")
        if task_data.get("status_id"):
            logger.debug(f"status_id: {task_data['status_id']}, type: {type(task_data['status_id'])}")
        if task_data.get("priority_id"):
            logger.debug(f"priority_id: {task_data['priority_id']}, type: {type(task_data['priority_id'])}")
        if task_data.get("duration_id"):
            logger.debug(f"duration_id: {task_data['duration_id']}, type: {type(task_data['duration_id'])}")
        
        # Выводим типы данных ID в настройках
        if settings.get("task_types") and len(settings["task_types"]) > 0:
            logger.debug(f"First task_type id: {settings['task_types'][0]['id']}, type: {type(settings['task_types'][0]['id'])}")
        if settings.get("statuses") and len(settings["statuses"]) > 0:
            logger.debug(f"First status id: {settings['statuses'][0]['id']}, type: {type(settings['statuses'][0]['id'])}")
        if settings.get("priorities") and len(settings["priorities"]) > 0:
            logger.debug(f"First priority id: {settings['priorities'][0]['id']}, type: {type(settings['priorities'][0]['id'])}")
        if settings.get("durations") and len(settings["durations"]) > 0:
            logger.debug(f"First duration id: {settings['durations'][0]['id']}, type: {type(settings['durations'][0]['id'])}")
        
        # Находим названия выбранных параметров
        type_name = "Не выбран"
        status_name = "Не выбран"
        priority_name = "Не выбран"
        duration_name = "Не выбрана"
        
        if task_data.get("type_id"):
            logger.debug(f"Looking for type_id: {task_data['type_id']} in {len(settings['task_types'])} task types")
            for task_type in settings["task_types"]:
                if str(task_type["id"]) == str(task_data["type_id"]):
                    type_name = task_type["name"]
                    logger.debug(f"Found type name: {type_name}")
                    break
                    
        if task_data.get("status_id"):
            logger.debug(f"Looking for status_id: {task_data['status_id']} in {len(settings['statuses'])} statuses")
            for status in settings["statuses"]:
                if str(status["id"]) == str(task_data["status_id"]):
                    status_name = status["name"]
                    logger.debug(f"Found status name: {status_name}")
                    break
                    
        if task_data.get("priority_id"):
            logger.debug(f"Looking for priority_id: {task_data['priority_id']} in {len(settings['priorities'])} priorities")
            for priority in settings["priorities"]:
                if str(priority["id"]) == str(task_data["priority_id"]):
                    priority_name = priority["name"]
                    logger.debug(f"Found priority name: {priority_name}")
                    break
                    
        if task_data.get("duration_id"):
            logger.debug(f"Looking for duration_id: {task_data['duration_id']} in {len(settings['durations'])} durations")
            for duration in settings["durations"]:
                if str(duration["id"]) == str(task_data["duration_id"]):
                    duration_name = duration["name"]
                    logger.debug(f"Found duration name: {duration_name}")
                    break
        
        result = {
            "title": task_data.get("title", "Новая задача"),
            "description": task_data.get("description", "Нет описания"),
            "type_name": type_name,
            "status_name": status_name,
            "priority_name": priority_name,
            "duration_name": duration_name
        }
        logger.debug(f"get_task_summary result: {result}")
        return result

async def main_process_result(start_data: Data, result: Any,
                              dialog_manager: DialogManager):
    logger.debug("main_process_result called!")
    logger.debug("Start data: %s", start_data)
    logger.debug("Result: %s", result)
    logger.debug("Dialog data: %s", dialog_manager.dialog_data)
    
    # Создаем задачу при завершении диалога
    if result:
        try:
            logger.debug("Creating task...")
            async with get_session() as session:
                task_service = TaskService(session)
                user_id = str(dialog_manager.event.from_user.id)
                logger.debug(f"User ID: {user_id}")
                task = await task_service.create_task(
                    user_id,
                    result
                )
                logger.debug(f"Task created: {task}")
                
                if task:
                    task_type = task['type']['name'] if task['type'] else i18n.format_value("type-not-set")
                    status = task['status']['name'] if task['status'] else i18n.format_value("status-not-set")
                    priority = task['priority']['name'] if task['priority'] else i18n.format_value("priority-not-set")
                    duration = task['duration']['name'] if task['duration'] else i18n.format_value("duration-not-set")
                    deadline = task['deadline'] if task['deadline'] else i18n.format_value("deadline-not-set")
                    
                    logger.debug(f"Sending task created message...")
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
                    logger.debug("Task created message sent")
        except Exception as e:
            logger.exception(f"Error creating task: {e}")
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
        Group(
            Select(
                Format("{item[name]}"),
                id="type",
                item_id_getter=lambda x: x["id"],
                items="task_types",
                on_click=on_type_selected,
            ),
            width=2,),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.type,
        getter=get_task_types,
    ),
    Window(
        Format(i18n.format_value("task-status")),
        Group(
            Select(
                Format("{item[name]}"),
                id="status",
                item_id_getter=lambda x: x["id"],
                items="statuses",
                on_click=on_status_selected,
            ),
            width=2,),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.status,
        getter=get_statuses,
    ),
    Window(
        Format(i18n.format_value("task-priority")),
        Group(
            Select(
                Format("{item[name]}"),
                id="priority",
                item_id_getter=lambda x: x["id"],
                items="priorities",
                on_click=on_priority_selected,
            ),
            width=2,),
        Row(
            Back(Const(i18n.format_value("back"))),
            Next(Const(i18n.format_value("next"))),
        ),
        state=TaskDialog.priority,
        getter=get_priorities,
    ),
    Window(
        Format(i18n.format_value("task-duration")),
        Group(
            Select(
                Format("{item[name]}"),
                id="duration",
                item_id_getter=lambda x: x["id"],
                items="durations",
                on_click=on_duration_selected,
            ),
            width=2,),
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