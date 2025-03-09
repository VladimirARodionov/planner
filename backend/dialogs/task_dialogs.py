from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
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

class TaskDialog(StatesGroup):
    title = State()
    description = State()
    type = State()
    status = State()
    priority = State()
    duration = State()

async def get_task_types(**kwargs):
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_types = await settings_service.get_task_types("system")
        return {"task_types": task_types}

async def get_statuses(**kwargs):
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses("system")
        return {"statuses": statuses}

async def get_priorities(**kwargs):
    async with get_session() as session:
        settings_service = SettingsService(session)
        priorities = await settings_service.get_priorities("system")
        return {"priorities": priorities}

async def get_durations(**kwargs):
    async with get_session() as session:
        settings_service = SettingsService(session)
        durations = await settings_service.get_durations("system")
        return {"durations": durations}

async def on_task_created(event, widget, manager: DialogManager):
    async with get_session() as session:
        task_service = TaskService(session)
        task = await task_service.create_task(
            str(event.from_user.id),
            manager.dialog_data
        )
        if task:
            task_type = task['type']['name'] if task['type'] else i18n.format_value("type-not-set")
            status = task['status']['name'] if task['status'] else i18n.format_value("status-not-set")
            priority = task['priority']['name'] if task['priority'] else i18n.format_value("priority-not-set")
            duration = task['duration']['name'] if task['duration'] else i18n.format_value("duration-not-set")
            deadline = task['deadline'] if task['deadline'] else i18n.format_value("deadline-not-set")
            
            await event.answer(
                i18n.format_value("task-created") + "\n\n" +
                i18n.format_value("task-created-details", {
                    "title": task['title'],
                    "description": task['description'] or i18n.format_value("status-not-set"),
                    "type": task_type,
                    "status": status,
                    "priority": priority,
                    "duration": duration,
                    "deadline": deadline
                })
            )
        else:
            await event.answer(i18n.format_value("error"))

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

async def on_status_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["status_id"] = item_id

async def on_priority_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["priority_id"] = item_id

async def on_duration_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["duration_id"] = item_id

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
            Button(Const(i18n.format_value("create")), id="create", on_click=on_task_created),
        ),
        state=TaskDialog.duration,
        getter=get_durations,
    ),
) 