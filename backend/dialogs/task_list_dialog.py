import logging
from datetime import timedelta

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import List, Format
from aiogram_dialog.widgets.kbd import NumberedPager, StubScroll
from aiogram_dialog.widgets.kbd import FirstPage, LastPage, NextPage, PrevPage, CurrentPage
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Row, Select, Group, Cancel, SwitchTo, Start
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.widget_event import SimpleEventProcessor
from typing import Any, Dict, List as TypeList, Optional, Callable
from aiogram_dialog.widgets.common import WhenCondition

from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService
from backend.database import get_session
from backend.utils import escape_html
from backend.dialogs.task_edit_dialog import TaskEditStates

logger = logging.getLogger(__name__)

# Пользовательский класс для списка задач с кнопками
class TaskList(List):
    def __init__(
        self,
        text_factory: Format,
        items: str,
        id: str,
        edit_button_text: Format,
        delete_button_text: Format,
        on_edit_click: Callable,
        on_delete_click: Callable,
        sep: str = "\n",
        page_size: Optional[int] = None,
        when: WhenCondition = None,
    ):
        # Вызываем конструктор базового класса с правильными параметрами
        super().__init__(
            field=text_factory,
            items=items,
            id=id,
            sep=sep,
            page_size=page_size,
            when=when
        )
        self.edit_button_text = edit_button_text
        self.delete_button_text = delete_button_text
        self.on_edit_click = on_edit_click
        self.on_delete_click = on_delete_click

    async def _render_text(self, data: Dict, manager: DialogManager) -> str:
        """Переопределяем метод _render_text для добавления кнопок к каждому элементу списка"""
        # Получаем элементы из данных с помощью items_getter
        items = self.items_getter(data)
        
        # Применяем пагинацию, если нужно
        pages = self._get_page_count(items)
        if self.page_size is None:
            current_page = 0
            start = 0
        else:
            last_page = pages - 1
            current_page = min(last_page, await self.get_page(manager))
            start = current_page * self.page_size
            items = items[start:start + self.page_size]
        
        if not items:
            return ""
        
        rendered_items = []
        for pos, item in enumerate(items, start):
            # Создаем контекст для рендеринга текста элемента
            item_context = {
                "current_page": current_page,
                "current_page1": current_page + 1,
                "pages": pages,
                "data": data,
                "item": item,
                "pos": pos + 1,
                "pos0": pos,
            }
            
            # Рендерим текст элемента с помощью field
            item_text = await self.field.render_text(item_context, manager)
            
            # Получаем ID задачи
            item_id = item["id"]
            
            # Форматируем кнопки
            edit_button = await self.edit_button_text.render_text({"item": item}, manager)
            delete_button = await self.delete_button_text.render_text({"item": item}, manager)
            
            # Добавляем кнопки к тексту задачи
            buttons = f"\n<a href='edit:{item_id}'>{edit_button}</a> | <a href='delete:{item_id}'>{delete_button}</a>"
            
            rendered_items.append(item_text + buttons)
        
        return self.sep.join(filter(None, rendered_items))
    
    async def process_event(self, event, manager: DialogManager) -> bool:
        """Обрабатывает события от кнопок в списке задач"""
        # Сначала проверяем, может ли базовый класс обработать событие
        if await super().process_event(event, manager):
            return True
            
        if not isinstance(event, CallbackQuery):
            return False
            
        data = event.data
        
        if data.startswith("edit:"):
            item_id = data.split(":", 1)[1]
            await self.on_edit_click(event, self, manager, item_id)
            return True
        
        if data.startswith("delete:"):
            item_id = data.split(":", 1)[1]
            await self.on_delete_click(event, self, manager, item_id)
            return True
        
        return False

# Определяем состояния для диалога списка задач
class TaskListStates(StatesGroup):
    main = State()  # Основной экран со списком задач
    filter_menu = State()  # Меню выбора фильтров
    filter_status = State()  # Фильтр по статусу
    filter_priority = State()  # Фильтр по приоритету
    filter_type = State()  # Фильтр по типу
    filter_deadline = State()  # Фильтр по дедлайну
    filter_completed = State()  # Фильтр по завершенности
    search = State()  # Поиск задач
    sort = State()  # Сортировка задач
    confirm_delete = State()  # Подтверждение удаления задачи

# Функции-обработчики для условий when
def has_error(data: dict, widget: Any, manager: DialogManager) -> bool:
    return "error" in data

def has_filters_and_description(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("has_filters", False) and data.get("filter_description")

def has_search_and_query(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("has_search", False) and data.get("search_query")

def has_sort_and_description(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("has_sort", False) and data.get("sort_description")

def has_tasks(data: dict, widget: Any, manager: DialogManager) -> bool:
    return len(data.get("tasks", [])) > 0

def has_no_tasks(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("total_tasks", 0) == 0

def has_multiple_pages(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("total_pages", 0) > 1

def has_more_than_two_pages(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("total_pages", 0) > 2

def is_not_first_page(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("page", 1) > 1

def is_not_last_page(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("page", 1) < data.get("total_pages", 1)

def is_not_last_page_and_more_than_two_pages(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("total_pages", 0) > 2 and data.get("page", 1) < data.get("total_pages", 1)

def has_filters(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("has_filters", False)

def has_sort(data: dict, widget: Any, manager: DialogManager) -> bool:
    return data.get("has_sort", False)

async def get_tasks_data(dialog_manager: DialogManager, **kwargs):
    """Получает данные о задачах пользователя для отображения в диалоге"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    if not user_id:
        logger.error("Не удалось получить ID пользователя")
        return {"tasks": [], "total_tasks": 0, "total_pages": 0, "page": 1}
    
    # Получаем текущую страницу из StubScroll, если он существует
    try:
        page = await dialog_manager.find("tasks_scroll").get_page() + 1  # +1 т.к. StubScroll считает с 0
        logger.info(f"Page from dialog_manager = {page}")
    except (AttributeError, ValueError):
        # Если StubScroll не найден или произошла ошибка, используем значение из dialog_data
        page = dialog_manager.dialog_data.get("page", dialog_manager.start_data.get("page", 1))
        logger.info(f"Page from except = {page}")

    # Сохраняем текущую страницу в dialog_data для совместимости
    dialog_manager.dialog_data["page"] = page
    
    # Получаем фильтры и параметры сортировки
    filters = dialog_manager.dialog_data.get("filters", dialog_manager.start_data.get("filters", {}))
    sort_by = dialog_manager.dialog_data.get("sort_by", dialog_manager.start_data.get("sort_by"))
    sort_order = dialog_manager.dialog_data.get("sort_order", dialog_manager.start_data.get("sort_order", "asc"))
    search_query = filters.get("search", "")
    
    # Безопасное отображение поискового запроса
    safe_search_query = search_query
    
    page_size = 3  # Количество задач на странице
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        logger.info(f"Page={page} page_size={page_size}")
        try:
            tasks, total_tasks = await task_service.get_tasks_paginated(
                str(user_id),
                page=page,
                page_size=page_size,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                search_query=safe_search_query
            )
        except Exception as e:
            logger.error(f"Ошибка при получении задач: {e}")
            return {"tasks": [], "total_tasks": 0, "total_pages": 0, "page": 1, "error": str(e)}
        
        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
        
        # Если запрошенная страница больше общего количества страниц, показываем последнюю страницу
        if page > total_pages and total_pages > 0:
            page = total_pages
            dialog_manager.dialog_data["page"] = page
            # Получаем задачи для последней страницы
            tasks, _ = await task_service.get_tasks_paginated(
                str(user_id),
                page=page,
                page_size=page_size,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                search_query=safe_search_query
            )
        
        # Обновляем StubScroll с текущей страницей (0-based)
        try:
            await dialog_manager.find("tasks_scroll").set_page(page - 1)
        except (AttributeError, ValueError):
            logger.warning("Не удалось обновить StubScroll")
        
        # Формируем описание фильтров
        filter_description = await get_filter_description(filters, str(user_id))
        
        # Формируем описание сортировки
        sort_description = ""
        if sort_by:
            sort_name = get_sort_name_display(sort_by)
            sort_direction = i18n.format_value(f"sort-direction-{sort_order}")
            sort_description = f"{sort_name} {sort_direction}"
        
        # Форматируем задачи для отображения в виджете List
        formatted_tasks = []
        for task in tasks:
            description = escape_html(task['description'] if task['description'] else "Нет описания")
            status = escape_html(task['status']['name'] if task['status'] else "Не указан")
            priority = escape_html(task['priority']['name'] if task['priority'] else "Не указан")
            task_type = escape_html(task['type']['name'] if task['type'] else "Не указан")
            deadline = escape_html(str(task['deadline']) if task['deadline'] else "Не указан")
            completed = "✅" if task['completed_at'] is not None else "❌"
            
            task_info = {
                "id": task['id'],
                "title": escape_html(task['title']),
                "description": description,
                "status": status,
                "priority": priority,
                "type": task_type,
                "deadline": deadline,
                "completed": completed,
                "is_completed": task['completed_at'] is not None
            }
            formatted_tasks.append(task_info)
        
        return {
            "tasks": formatted_tasks,
            "total_tasks": total_tasks,
            "total_pages": total_pages,
            "page": page,
            "has_filters": bool(filters),
            "filter_description": filter_description,
            "has_search": bool(safe_search_query),
            "search_query": safe_search_query,
            "has_sort": bool(sort_by),
            "sort_description": sort_description
        }

async def get_statuses(dialog_manager: DialogManager, **kwargs):
    """Получает список статусов для фильтрации"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"statuses": settings["statuses"]}

async def get_priorities(dialog_manager: DialogManager, **kwargs):
    """Получает список приоритетов для фильтрации"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"priorities": settings["priorities"]}

async def get_task_types(dialog_manager: DialogManager, **kwargs):
    """Получает список типов задач для фильтрации"""
    user_id = dialog_manager.event.from_user.id if hasattr(dialog_manager.event, 'from_user') else None
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(str(user_id) if user_id else None)
        return {"task_types": settings["task_types"]}

async def get_filter_description(filters: dict, user_id: str = None) -> str:
    """Формирует описание примененных фильтров для отображения пользователю"""
    if not filters:
        return ""
    
    # Удаляем поисковый запрос из фильтров для описания
    filters_copy = filters.copy()
    filters_copy.pop('search', None)
    
    if not filters_copy:
        return ""
    
    filter_parts = []
    
    # Получаем все настройки один раз
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings(user_id)
        
        statuses = {status["id"]: escape_html(status["name"]) for status in settings["statuses"]}
        priorities = {priority["id"]: escape_html(priority["name"]) for priority in settings["priorities"]}
        task_types = {task_type["id"]: escape_html(task_type["name"]) for task_type in settings["task_types"]}
    
    if 'status_id' in filters_copy:
        status_name = statuses.get(filters_copy['status_id'], f"Статус {filters_copy['status_id']}")
        filter_parts.append(f"Статус: {status_name}")
    
    if 'priority_id' in filters_copy:
        priority_name = priorities.get(filters_copy['priority_id'], f"Приоритет {filters_copy['priority_id']}")
        filter_parts.append(f"Приоритет: {priority_name}")
    
    if 'type_id' in filters_copy:
        type_name = task_types.get(filters_copy['type_id'], f"Тип {filters_copy['type_id']}")
        filter_parts.append(f"Тип: {type_name}")
    
    if 'deadline_from' in filters_copy:
        deadline_from = escape_html(str(filters_copy['deadline_from']))
        filter_parts.append(f"Дедлайн от: {deadline_from}")
    
    if 'deadline_to' in filters_copy:
        deadline_to = escape_html(str(filters_copy['deadline_to']))
        filter_parts.append(f"Дедлайн до: {deadline_to}")
    
    if 'is_completed' in filters_copy:
        completed_status = "Завершенные" if filters_copy['is_completed'] else "Незавершенные"
        filter_parts.append(f"Статус: {completed_status}")
    
    return ", ".join(filter_parts)

def get_sort_name_display(sort_by: str) -> str:
    """Получить отображаемое имя поля сортировки"""
    sort_field_key = f"sort-field-{sort_by}"
    return i18n.format_value(sort_field_key)

# Обработчики событий
async def on_page_prev(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик перехода на предыдущую страницу"""
    # Просто уменьшаем номер страницы, но не меньше 1
    page = manager.dialog_data.get("page", 1)
    if page > 1:
        page -= 1
        manager.dialog_data["page"] = page
        
        # Обновляем StubScroll с текущей страницей (0-based)
        try:
            await manager.find("tasks_scroll").set_page(page - 1)
        except (AttributeError, ValueError):
            logger.warning("Не удалось обновить StubScroll в on_page_prev")
    
    await manager.update(data={})

async def on_page_next(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик перехода на следующую страницу"""
    # Просто увеличиваем номер страницы, проверка на максимальное количество страниц
    # будет выполнена в getter-функции
    page = manager.dialog_data.get("page", 1)
    page += 1
    manager.dialog_data["page"] = page
    
    # Обновляем StubScroll с текущей страницей (0-based)
    try:
        await manager.find("tasks_scroll").set_page(page - 1)
    except (AttributeError, ValueError):
        logger.warning("Не удалось обновить StubScroll в on_page_next")
    
    await manager.update(data={})

async def on_reset_filters(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик сброса фильтров"""
    manager.dialog_data["filters"] = {}
    await manager.update(data={})

async def on_reset_sort(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик сброса сортировки"""
    manager.dialog_data.pop("sort_by", None)
    manager.dialog_data.pop("sort_order", None)
    await manager.update(data={})

async def on_status_selected(c: CallbackQuery, select: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора статуса для фильтрации"""
    filters = manager.dialog_data.get("filters", {})
    filters["status_id"] = item_id
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_priority_selected(c: CallbackQuery, select: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора приоритета для фильтрации"""
    filters = manager.dialog_data.get("filters", {})
    filters["priority_id"] = item_id
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_type_selected(c: CallbackQuery, select: Any, manager: DialogManager, item_id: str):
    """Обработчик выбора типа задачи для фильтрации"""
    filters = manager.dialog_data.get("filters", {})
    filters["type_id"] = item_id
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_completed_all(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора показа всех задач (и завершенных, и незавершенных)"""
    filters = manager.dialog_data.get("filters", {})
    if "is_completed" in filters:
        filters.pop("is_completed")
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_completed_only(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора показа только завершенных задач"""
    filters = manager.dialog_data.get("filters", {})
    filters["is_completed"] = True
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_uncompleted_only(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора показа только незавершенных задач"""
    filters = manager.dialog_data.get("filters", {})
    filters["is_completed"] = False
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_deadline_today(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора фильтра по дедлайну на сегодня"""
    from datetime import datetime
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    filters = manager.dialog_data.get("filters", {})
    filters["deadline_from"] = today
    filters["deadline_to"] = today
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_deadline_tomorrow(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора фильтра по дедлайну на завтра"""
    from datetime import datetime, timedelta
    tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    filters = manager.dialog_data.get("filters", {})
    filters["deadline_from"] = tomorrow
    filters["deadline_to"] = tomorrow
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_deadline_week(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора фильтра по дедлайну на текущую неделю"""
    from datetime import datetime, timedelta
    today = datetime.now().date()
    start_of_week = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    end_of_week = (today + timedelta(days=6-today.weekday())).strftime("%Y-%m-%d")
    
    filters = manager.dialog_data.get("filters", {})
    filters["deadline_from"] = start_of_week
    filters["deadline_to"] = end_of_week
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_deadline_month(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора фильтра по дедлайну на текущий месяц"""
    from datetime import datetime
    today = datetime.now().date()
    start_of_month = today.replace(day=1).strftime("%Y-%m-%d")
    
    # Определяем последний день месяца
    if today.month == 12:
        end_of_month = today.replace(day=31).strftime("%Y-%m-%d")
    else:
        next_month = today.replace(month=today.month + 1, day=1)
        from datetime import timedelta
        end_of_month = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
    
    filters = manager.dialog_data.get("filters", {})
    filters["deadline_from"] = start_of_month
    filters["deadline_to"] = end_of_month
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_deadline_overdue(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора фильтра по просроченным задачам"""
    from datetime import datetime
    yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    filters = manager.dialog_data.get("filters", {})
    filters["deadline_to"] = yesterday
    if "deadline_from" in filters:
        filters.pop("deadline_from")
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_sort_by_title(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по названию"""
    manager.dialog_data["sort_by"] = "title"
    await manager.switch_to(TaskListStates.main)

async def on_sort_by_deadline(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по дедлайну"""
    manager.dialog_data["sort_by"] = "deadline"
    await manager.switch_to(TaskListStates.main)

async def on_sort_by_priority(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по приоритету"""
    manager.dialog_data["sort_by"] = "priority"
    await manager.switch_to(TaskListStates.main)

async def on_sort_by_created(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по дате создания"""
    manager.dialog_data["sort_by"] = "created_at"
    await manager.switch_to(TaskListStates.main)

async def on_sort_asc(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по возрастанию"""
    manager.dialog_data["sort_order"] = "asc"
    await manager.switch_to(TaskListStates.main)

async def on_sort_desc(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора сортировки по убыванию"""
    manager.dialog_data["sort_order"] = "desc"
    await manager.switch_to(TaskListStates.main)

async def on_search_query_input(message: Message, widget: Any, manager: DialogManager, data: dict = None):
    """Обработчик ввода поискового запроса"""
    # Экранируем специальные символы в поисковом запросе
    search_query = escape_html(message.text.strip())
    
    filters = manager.dialog_data.get("filters", {})
    filters["search"] = search_query
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_page_selected(c: CallbackQuery, button: Any, manager: DialogManager, page: int):
    """Обработчик выбора страницы в NumberedPager"""
    manager.dialog_data["page"] = page
    # Обновляем StubScroll с текущей страницей (0-based)
    try:
        await manager.find("tasks_scroll").set_page(page - 1)
    except (AttributeError, ValueError):
        logger.warning("Не удалось обновить StubScroll")
    await manager.update(data={})

async def on_edit_task_click(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик нажатия на кнопку редактирования задачи"""
    await manager.start(TaskEditStates.main, data={"task_id": item_id})

async def on_delete_task_click(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    """Обработчик нажатия на кнопку удаления задачи"""
    manager.dialog_data["task_to_delete"] = item_id
    await manager.switch_to(TaskListStates.confirm_delete)

async def on_confirm_delete(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик подтверждения удаления задачи"""
    user_id = str(manager.event.from_user.id)
    task_id = manager.dialog_data.get("task_to_delete")
    
    if not task_id:
        await c.answer(i18n.format_value("task-delete-error-no-id"))
        await manager.switch_to(TaskListStates.main)
        return
    
    async with get_session() as session:
        task_service = TaskService(session)
        success = await task_service.delete_task(user_id, task_id)
        
        if success:
            await c.answer(i18n.format_value("task-delete-success", {"id": task_id}))
        else:
            await c.answer(i18n.format_value("task-delete-error", {"id": task_id}))
    
    await manager.switch_to(TaskListStates.main)

async def on_cancel_delete(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик отмены удаления задачи"""
    await manager.switch_to(TaskListStates.main)

# Создаем диалог для списка задач
task_list_dialog = Dialog(
    # Основной экран со списком задач
    Window(
        # Создаем StubScroll для управления пагинацией
        StubScroll(
            id="tasks_scroll",
            pages="total_pages"
        ),
        
        # Заголовок с информацией о странице и общем количестве задач
        Format(i18n.format_value("task-list-title", {"page": "{page}", "total_pages": "{total_pages}", "total_tasks": "{total_tasks}"})),
        
        # Сообщение об ошибке, если она возникла
        Format(i18n.format_value("task-list-error", {"error": "{error}"}), when=has_error),
        
        # Информация о фильтрах, если они есть
        Format(i18n.format_value("task-list-filter-description", {"filter_description": "{filter_description}"}), when=has_filters_and_description),
        
        # Информация о поисковом запросе, если он есть
        Format(i18n.format_value("task-list-search-query", {"search_query": "{search_query}"}), when=has_search_and_query),
        
        # Информация о сортировке, если она есть
        Format(i18n.format_value("task-list-sort-description", {"sort_description": "{sort_description}"}), when=has_sort_and_description),
        
        # Список задач с использованием пользовательского виджета TaskList
        TaskList(
            Format(
                i18n.format_value("task-list-item", {
                    "title": "{item[title]}",
                    "id": "{item[id]}",
                    "description": "{item[description]}",
                    "type": "{item[type]}",
                    "status": "{item[status]}",
                    "priority": "{item[priority]}",
                    "deadline": "{item[deadline]}",
                    "completed": "{item[completed]}"
                })
            ),
            items="tasks",
            id="tasks_list",
            edit_button_text=Format(i18n.format_value("task-list-edit-button", {"id": "{item[id]}"})),
            delete_button_text=Format(i18n.format_value("task-list-delete-button", {"id": "{item[id]}"})),
            on_edit_click=on_edit_task_click,
            on_delete_click=on_delete_task_click,
            sep="\n\n",
            page_size=3,
            when=has_tasks
        ),
        
        # Сообщение, если задач нет
        Format(i18n.format_value("task-list-empty"), when=has_no_tasks),
        
        # Пагинация для списка задач с использованием NumberedPager
        NumberedPager(
            scroll="tasks_scroll",
            page_text=Format("{target_page}\uFE0F\u20E3"),
            current_page_text=Format("{current_page}"),
            when=has_multiple_pages
        ),
        
        # Альтернативная навигация по страницам
        Row(
            FirstPage(
                scroll="tasks_scroll",
                text=Format("⏮️ {target_page}"),
                when=has_more_than_two_pages
            ),
            PrevPage(
                scroll="tasks_scroll",
                text=Format("◀️"),
                when=is_not_first_page
            ),
            CurrentPage(
                scroll="tasks_scroll",
                text=Format("{current_page}/{total_pages}"),
                when=has_multiple_pages
            ),
            NextPage(
                scroll="tasks_scroll",
                text=Format("▶️"),
                when=is_not_last_page
            ),
            LastPage(
                scroll="tasks_scroll",
                text=Format("{target_page} ⏭️"),
                when=is_not_last_page_and_more_than_two_pages
            ),
            when=has_multiple_pages
        ),
        
        # Простые кнопки навигации (не зависят от StubScroll)
        Row(
            Button(Const("◀️ Назад"), id="prev_page", on_click=on_page_prev, when=is_not_first_page),
            Button(Const("Вперед ▶️"), id="next_page", on_click=on_page_next, when=is_not_last_page),
            when=has_multiple_pages
        ),
        
        # Кнопки действий
        Row(
            SwitchTo(Const(i18n.format_value("task-list-filter-button")), id="to_filter", state=TaskListStates.filter_menu),
            SwitchTo(Const(i18n.format_value("task-list-search-button")), id="to_search", state=TaskListStates.search),
            SwitchTo(Const(i18n.format_value("task-list-sort-button")), id="to_sort", state=TaskListStates.sort),
        ),
        
        # Кнопки сброса фильтров и сортировки
        Row(
            Button(Const(i18n.format_value("task-list-reset-filters-button")), id="reset_filters", on_click=on_reset_filters, when=has_filters),
            Button(Const(i18n.format_value("task-list-reset-sort-button")), id="reset_sort", on_click=on_reset_sort, when=has_sort),
        ),
        
        # Кнопка закрытия диалога
        Row(
            Cancel(Const(i18n.format_value("task-list-close-button"))),
        ),
        
        state=TaskListStates.main,
        getter=get_tasks_data,
    ),
    
    # Экран выбора типа фильтра
    Window(
        Const(i18n.format_value("task-list-filter-menu-title")),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-filter-status-button")), id="to_status", state=TaskListStates.filter_status),
            SwitchTo(Const(i18n.format_value("task-list-filter-priority-button")), id="to_priority", state=TaskListStates.filter_priority),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-filter-type-button")), id="to_type", state=TaskListStates.filter_type),
            SwitchTo(Const(i18n.format_value("task-list-filter-deadline-button")), id="to_deadline", state=TaskListStates.filter_deadline),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-filter-completed-button")), id="to_completed", state=TaskListStates.filter_completed),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.filter_menu,
    ),
    
    # Экран фильтра по статусу
    Window(
        Const(i18n.format_value("task-list-filter-status-title")),
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
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_status,
        getter=get_statuses,
    ),
    
    # Экран фильтра по приоритету
    Window(
        Const(i18n.format_value("task-list-filter-priority-title")),
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
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_priority,
        getter=get_priorities,
    ),
    
    # Экран фильтра по типу задачи
    Window(
        Const(i18n.format_value("task-list-filter-type-title")),
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
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_type,
        getter=get_task_types,
    ),
    
    # Экран фильтра по дедлайну
    Window(
        Const(i18n.format_value("task-list-filter-deadline-title")),
        Row(
            Button(Const(i18n.format_value("task-list-filter-deadline-today")), id="deadline_today", on_click=on_deadline_today),
            Button(Const(i18n.format_value("task-list-filter-deadline-tomorrow")), id="deadline_tomorrow", on_click=on_deadline_tomorrow),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-filter-deadline-week")), id="deadline_week", on_click=on_deadline_week),
            Button(Const(i18n.format_value("task-list-filter-deadline-month")), id="deadline_month", on_click=on_deadline_month),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-filter-deadline-overdue")), id="deadline_overdue", on_click=on_deadline_overdue),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_deadline,
    ),
    
    # Экран фильтра по завершенности
    Window(
        Const(i18n.format_value("task-list-filter-completed-title")),
        Row(
            Button(Const(i18n.format_value("task-list-filter-completed-all")), id="completed_all", on_click=on_completed_all),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-filter-uncompleted-only")), id="uncompleted_only", on_click=on_uncompleted_only),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-filter-completed-only")), id="completed_only", on_click=on_completed_only),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_completed,
    ),
    
    # Экран сортировки
    Window(
        Const(i18n.format_value("task-list-sort-title")),
        Row(
            Button(Const(i18n.format_value("task-list-sort-by-title")), id="sort_title", on_click=on_sort_by_title),
            Button(Const(i18n.format_value("task-list-sort-by-deadline")), id="sort_deadline", on_click=on_sort_by_deadline),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-sort-by-priority")), id="sort_priority", on_click=on_sort_by_priority),
            Button(Const(i18n.format_value("task-list-sort-by-created")), id="sort_created", on_click=on_sort_by_created),
        ),
        Row(
            Button(Const(i18n.format_value("task-list-sort-asc")), id="sort_asc", on_click=on_sort_asc),
            Button(Const(i18n.format_value("task-list-sort-desc")), id="sort_desc", on_click=on_sort_desc),
        ),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-back-button")), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.sort,
    ),
    
    # Экран поиска
    Window(
        Const(i18n.format_value("task-list-search-title")),
        TextInput(id="search_query", on_success=SimpleEventProcessor(on_search_query_input)),
        Row(
            SwitchTo(Const(i18n.format_value("task-list-search-cancel")), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.search,
    ),
    
    # Экран подтверждения удаления задачи
    Window(
        Const(i18n.format_value("task-delete-confirm-title")),
        Format(i18n.format_value("task-delete-confirm-text", {"id": "{task_to_delete}"})),
        Row(
            Button(Const(i18n.format_value("task-delete-confirm-yes")), id="confirm_delete", on_click=on_confirm_delete),
            Button(Const(i18n.format_value("task-delete-confirm-no")), id="cancel_delete", on_click=on_cancel_delete),
        ),
        state=TaskListStates.confirm_delete,
    ),
) 