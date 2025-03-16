import logging
from datetime import datetime

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.kbd import Button, Select, Back, Next, Row, Group, Cancel, SwitchTo, Calendar
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog import DialogManager
from typing import Any
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.widget_event import SimpleEventProcessor

from backend.custom_widgets import I18NFormat
from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService
from backend.database import get_session
from backend.utils import escape_html

logger = logging.getLogger(__name__)

class TaskEditStates(StatesGroup):
    main = State()  # Главный экран редактирования с выбором поля
    title = State()  # Редактирование заголовка
    description = State()  # Редактирование описания
    type = State()  # Выбор типа
    status = State()  # Выбор статуса
    priority = State()  # Выбор приоритета
    duration = State()  # Выбор продолжительности
    deadline = State()  # Выбор дедлайна
    confirm = State()  # Подтверждение изменений

# Функции для получения данных
async def get_task_data(dialog_manager: DialogManager, **kwargs):
    """Получает данные о задаче для редактирования"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    task_id = dialog_manager.start_data.get("task_id")
    
    if not user_id or not task_id:
        logger.error(f"Не удалось получить ID пользователя или задачи. user_id={user_id}, task_id={task_id}")
        return {"error": "Не удалось получить данные задачи"}
    
    # Если данные задачи уже загружены, используем их
    if "task" in dialog_manager.dialog_data:
        task = dialog_manager.dialog_data["task"]
        # Правильно форматируем completed_at, проверяя тип данных
        completed_at_display = None
        if task["completed_at"]:
            if isinstance(task["completed_at"], datetime):
                completed_at_display = task["completed_at"].strftime("%d.%m.%Y %H:%M")
            elif isinstance(task["completed_at"], str):
                try:
                    # Пытаемся преобразовать строку в datetime
                    completed_at_datetime = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00'))
                    completed_at_display = completed_at_datetime.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, используем как есть
                    completed_at_display = task["completed_at"]
        
        return {
            "task_id": task["id"],
            "title": escape_html(task["title"]),
            "description": escape_html(task["description"] or ""),
            "type_id": task["type"]["id"] if task["type"] else None,
            "type_name": escape_html(task["type"]["name"]) if task["type"] else "Не выбран",
            "status_id": task["status"]["id"] if task["status"] else None,
            "status_name": escape_html(task["status"]["name"]) if task["status"] else "Не выбран",
            "priority_id": task["priority"]["id"] if task["priority"] else None,
            "priority_name": escape_html(task["priority"]["name"]) if task["priority"] else "Не выбран",
            "duration_id": task["duration"]["id"] if task["duration"] else None,
            "duration_name": escape_html(task["duration"]["name"]) if task["duration"] else "Не выбрана",
            "deadline": task["deadline"] if task["deadline"] else None,
            "deadline_display": task["deadline"].strftime("%d.%m.%Y") if isinstance(task["deadline"], datetime) else task["deadline"] if task["deadline"] else "Не установлен",
            "completed": task["completed_at"] is not None,
            "completed_at": completed_at_display
        }
    
    # Загружаем данные задачи из БД
    async with get_session() as session:
        task_service = TaskService(session)
        # Получаем задачу по ID
        tasks = await task_service.get_tasks(
            str(user_id),
            filters={"id": task_id}
        )
        
        if not tasks or len(tasks) == 0:
            logger.error(f"Задача с ID {task_id} не найдена для пользователя {user_id}")
            return {"error": "Задача не найдена"}
        
        task = tasks[0]  # Берем первую задачу из результата
        
        # Сохраняем задачу в dialog_data для последующего использования
        dialog_manager.dialog_data["task"] = task
        dialog_manager.dialog_data["original_task"] = task.copy()  # Сохраняем оригинальные данные
        
        # Правильно форматируем completed_at, проверяя тип данных
        completed_at_display = None
        if task["completed_at"]:
            if isinstance(task["completed_at"], datetime):
                completed_at_display = task["completed_at"].strftime("%d.%m.%Y %H:%M")
            elif isinstance(task["completed_at"], str):
                try:
                    # Пытаемся преобразовать строку в datetime
                    completed_at_datetime = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00'))
                    completed_at_display = completed_at_datetime.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, используем как есть
                    completed_at_display = task["completed_at"]
        
        return {
            "task_id": task["id"],
            "title": escape_html(task["title"]),
            "description": escape_html(task["description"] or ""),
            "type_id": task["type"]["id"] if task["type"] else None,
            "type_name": escape_html(task["type"]["name"]) if task["type"] else "Не выбран",
            "status_id": task["status"]["id"] if task["status"] else None,
            "status_name": escape_html(task["status"]["name"]) if task["status"] else "Не выбран",
            "priority_id": task["priority"]["id"] if task["priority"] else None,
            "priority_name": escape_html(task["priority"]["name"]) if task["priority"] else "Не выбран",
            "duration_id": task["duration"]["id"] if task["duration"] else None,
            "duration_name": escape_html(task["duration"]["name"]) if task["duration"] else "Не выбрана",
            "deadline": task["deadline"] if task["deadline"] else None,
            "deadline_display": task["deadline"].strftime("%d.%m.%Y") if isinstance(task["deadline"], datetime) else task["deadline"] if task["deadline"] else "Не установлен",
            "completed": task["completed_at"] is not None,
            "completed_at": completed_at_display
        }

async def get_task_types(dialog_manager: DialogManager, **kwargs):
    """Получает список типов задач"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"task_types": settings["task_types"]}

async def get_statuses(dialog_manager: DialogManager, **kwargs):
    """Получает список статусов"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"statuses": settings["statuses"]}

async def get_priorities(dialog_manager: DialogManager, **kwargs):
    """Получает список приоритетов"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"priorities": settings["priorities"]}

async def get_durations(dialog_manager: DialogManager, **kwargs):
    """Получает список продолжительностей"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"durations": settings["durations"]}

# Обработчики событий
async def on_title_success(message: Message, widget: Any, manager: DialogManager, *args, **kwargs):
    """Обработчик ввода заголовка"""
    if message.text and message.text.strip():
        task = manager.dialog_data.get("task", {})
        task["title"] = message.text.strip()
        manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_description_success(message: Message, widget: Any, manager: DialogManager, *args, **kwargs):
    """Обработчик ввода описания"""
    task = manager.dialog_data.get("task", {})
    task["description"] = None if message.text == '-' else message.text
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_type_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора типа задачи"""
    task = manager.dialog_data.get("task", {})
    
    if item_id == "none":
        task["type"] = None
    else:
        async with get_session() as session:
            settings_service = SettingsService(session)
            user_id = str(manager.event.from_user.id)
            settings = await settings_service.get_settings(user_id)
            
            for task_type in settings["task_types"]:
                if str(task_type["id"]) == str(item_id):
                    task["type"] = task_type
                    break
    
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_status_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора статуса"""
    task = manager.dialog_data.get("task", {})
    
    if item_id == "none":
        task["status"] = None
    else:
        async with get_session() as session:
            settings_service = SettingsService(session)
            user_id = str(manager.event.from_user.id)
            settings = await settings_service.get_settings(user_id)
            
            for status in settings["statuses"]:
                if str(status["id"]) == str(item_id):
                    task["status"] = status
                    break
    
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_priority_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора приоритета"""
    task = manager.dialog_data.get("task", {})
    
    if item_id == "none":
        task["priority"] = None
    else:
        async with get_session() as session:
            settings_service = SettingsService(session)
            user_id = str(manager.event.from_user.id)
            settings = await settings_service.get_settings(user_id)
            
            for priority in settings["priorities"]:
                if str(priority["id"]) == str(item_id):
                    task["priority"] = priority
                    break
    
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_duration_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора продолжительности"""
    task = manager.dialog_data.get("task", {})
    
    if item_id == "none":
        task["duration"] = None
    else:
        async with get_session() as session:
            settings_service = SettingsService(session)
            user_id = str(manager.event.from_user.id)
            settings = await settings_service.get_settings(user_id)
            
            for duration in settings["durations"]:
                if str(duration["id"]) == str(item_id):
                    task["duration"] = duration
                    break
    
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_deadline_selected(c: CallbackQuery, widget: Any, manager: DialogManager, date: datetime):
    """Обработчик выбора дедлайна"""
    task = manager.dialog_data.get("task", {})
    task["deadline"] = date
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_deadline_clear(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик очистки дедлайна"""
    task = manager.dialog_data.get("task", {})
    task["deadline"] = None
    manager.dialog_data["task"] = task
    await manager.switch_to(TaskEditStates.main)

async def on_toggle_completed(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик переключения статуса завершения"""
    task = manager.dialog_data.get("task", {})
    
    if task.get("completed_at") is None:
        task["completed_at"] = datetime.now()
    else:
        task["completed_at"] = None
    
    manager.dialog_data["task"] = task
    await manager.update()

async def on_save_changes(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик сохранения изменений"""
    user_id = str(manager.event.from_user.id)
    task = manager.dialog_data.get("task", {})
    
    try:
        async with get_session() as session:
            task_service = TaskService(session)
            
            # Подготавливаем данные для обновления
            update_data = {
                "title": task["title"],
                "description": task["description"],
                "type_id": task["type"]["id"] if task.get("type") else None,
                "status_id": task["status"]["id"] if task.get("status") else None,
                "priority_id": task["priority"]["id"] if task.get("priority") else None,
                "duration_id": task["duration"]["id"] if task.get("duration") else None,
                "deadline": task.get("deadline"),
                "completed_at": task.get("completed_at")
            }
            
            # Обновляем задачу
            updated_task = await task_service.update_task(user_id, task["id"], update_data)
            
            if updated_task:
                await callback.answer(i18n.format_value("task-edit-success"))
                await manager.done({"updated": True})
            else:
                await callback.answer(i18n.format_value("task-edit-error-update"))
    except Exception as e:
        logger.exception(f"Ошибка при обновлении задачи: {e}")
        await callback.answer(i18n.format_value("task-edit-error-generic", {"error": str(e)}))

# Функции для условий when
def has_error(data: dict, widget: Any, manager: DialogManager) -> bool:
    return "error" in data

def is_completed(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("completed", False)

def is_not_completed(data: dict, widget: Any, manager: DialogManager) -> bool:
    return not data.get("completed", False)

# Создаем диалог редактирования задачи
task_edit_dialog = Dialog(
    # Главный экран с информацией о задаче и кнопками для редактирования
    Window(
        I18NFormat("task-edit-title"),
        I18NFormat("task-edit-error", {"error": "{error}"}, when=has_error),
        I18NFormat("task-edit-details", {
                "title": "{title}",
                "description": "{description}",
                "type_name": "{type_name}",
                "status_name": "{status_name}",
                "priority_name": "{priority_name}",
                "duration_name": "{duration_name}",
                "deadline_display": "{deadline_display}",
                "completed": "{completed}",
                "completed_at": "{completed_at}"
            }
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-title"), id="edit_title", state=TaskEditStates.title),
            SwitchTo(I18NFormat("task-edit-button-description"), id="edit_description", state=TaskEditStates.description),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-type"), id="edit_type", state=TaskEditStates.type),
            SwitchTo(I18NFormat("task-edit-button-status"), id="edit_status", state=TaskEditStates.status),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-priority"), id="edit_priority", state=TaskEditStates.priority),
            SwitchTo(I18NFormat("task-edit-button-duration"), id="edit_duration", state=TaskEditStates.duration),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-deadline"), id="edit_deadline", state=TaskEditStates.deadline),
        ),
        Row(
            Button(I18NFormat("task-edit-button-mark-completed"), id="toggle_completed", on_click=on_toggle_completed, when=is_not_completed),
            Button(I18NFormat("task-edit-button-mark-uncompleted"), id="toggle_completed", on_click=on_toggle_completed, when=is_completed),
        ),
        Row(
            Button(I18NFormat("task-edit-button-save"), id="save", on_click=on_save_changes),
            Cancel(I18NFormat("task-edit-button-cancel")),
        ),
        state=TaskEditStates.main,
        getter=get_task_data,
    ),
    
    # Экран редактирования заголовка
    Window(
        I18NFormat("task-edit-title-prompt"),
        TextInput(id="title", on_success=SimpleEventProcessor(on_title_success)),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.title,
    ),
    
    # Экран редактирования описания
    Window(
        I18NFormat("task-edit-description-prompt"),
        I18NFormat("task-edit-description-hint"),
        TextInput(id="description", on_success=SimpleEventProcessor(on_description_success)),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.description,
    ),
    
    # Экран выбора типа задачи
    Window(
        I18NFormat("task-edit-type-prompt"),
        Group(
            Select(
                Format("{item[name]}"),
                id="type",
                item_id_getter=lambda x: x["id"],
                items="task_types",
                on_click=on_type_selected,
            ),
            width=2,
        ),
        Row(
            Button(I18NFormat("task-edit-button-clear"), id="clear_type", on_click=lambda c, b, m: on_type_selected(c, b, m, "none")),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.type,
        getter=get_task_types,
    ),
    
    # Экран выбора статуса
    Window(
        I18NFormat("task-edit-status-prompt"),
        Group(
            Select(
                Format("{item[name]}"),
                id="status",
                item_id_getter=lambda x: x["id"],
                items="statuses",
                on_click=on_status_selected,
            ),
            width=2,
        ),
        Row(
            Button(I18NFormat("task-edit-button-clear"), id="clear_status", on_click=lambda c, b, m: on_status_selected(c, b, m, "none")),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.status,
        getter=get_statuses,
    ),
    
    # Экран выбора приоритета
    Window(
        I18NFormat("task-edit-priority-prompt"),
        Group(
            Select(
                Format("{item[name]}"),
                id="priority",
                item_id_getter=lambda x: x["id"],
                items="priorities",
                on_click=on_priority_selected,
            ),
            width=2,
        ),
        Row(
            Button(I18NFormat("task-edit-button-clear"), id="clear_priority", on_click=lambda c, b, m: on_priority_selected(c, b, m, "none")),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.priority,
        getter=get_priorities,
    ),
    
    # Экран выбора продолжительности
    Window(
        I18NFormat("task-edit-duration-prompt"),
        Group(
            Select(
                Format("{item[name]}"),
                id="duration",
                item_id_getter=lambda x: x["id"],
                items="durations",
                on_click=on_duration_selected,
            ),
            width=2,
        ),
        Row(
            Button(I18NFormat("task-edit-button-clear"), id="clear_duration", on_click=lambda c, b, m: on_duration_selected(c, b, m, "none")),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.duration,
        getter=get_durations,
    ),
    
    # Экран выбора дедлайна
    Window(
        I18NFormat("task-edit-deadline-prompt"),
        Calendar(
            id="deadline_calendar",
            on_click=on_deadline_selected
        ),
        Row(
            Button(I18NFormat("task-edit-button-clear-deadline"), id="clear_deadline", on_click=on_deadline_clear),
        ),
        Row(
            SwitchTo(I18NFormat("task-edit-button-back"), id="back_to_main", state=TaskEditStates.main),
        ),
        state=TaskEditStates.deadline,
    ),
) 