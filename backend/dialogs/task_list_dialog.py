import logging
from datetime import timedelta

from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import List
from aiogram_dialog.widgets.kbd import NumberedPager, StubScroll
from aiogram_dialog.widgets.kbd import FirstPage, LastPage, NextPage, PrevPage, CurrentPage
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Select, Group, Cancel, SwitchTo
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.widget_event import SimpleEventProcessor
from typing import Any

from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService
from backend.database import get_session

logger = logging.getLogger(__name__)

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
    except (AttributeError, ValueError):
        # Если StubScroll не найден или произошла ошибка, используем значение из dialog_data
        page = dialog_manager.dialog_data.get("page", dialog_manager.start_data.get("page", 1))
    
    # Сохраняем текущую страницу в dialog_data для совместимости
    dialog_manager.dialog_data["page"] = page
    
    # Получаем фильтры и параметры сортировки
    filters = dialog_manager.dialog_data.get("filters", dialog_manager.start_data.get("filters", {}))
    sort_by = dialog_manager.dialog_data.get("sort_by", dialog_manager.start_data.get("sort_by"))
    sort_order = dialog_manager.dialog_data.get("sort_order", dialog_manager.start_data.get("sort_order", "asc"))
    search_query = filters.get("search", "")
    
    page_size = 3  # Количество задач на странице
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        try:
            tasks, total_tasks = await task_service.get_tasks_paginated(
                str(user_id),
                page=page,
                page_size=page_size,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                search_query=search_query
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
                search_query=search_query
            )
        
        # Формируем описание фильтров
        filter_description = await get_filter_description(filters, user_id)
        
        # Формируем описание сортировки
        sort_description = ""
        if sort_by:
            sort_name = get_sort_name_display(sort_by)
            sort_direction = "по возрастанию" if sort_order == "asc" else "по убыванию"
            sort_description = f"{sort_name} {sort_direction}"
        
        # Форматируем задачи для отображения в виджете List
        formatted_tasks = []
        for task in tasks:
            description = task['description'] if task['description'] else "Нет описания"
            status = task['status']['name'] if task['status'] else "Не указан"
            priority = task['priority']['name'] if task['priority'] else "Не указан"
            task_type = task['type']['name'] if task['type'] else "Не указан"
            deadline = task['deadline'] if task['deadline'] else "Не указан"
            completed = "✅" if task['completed_at'] is not None else "❌"
            
            task_info = {
                "id": task['id'],
                "title": task['title'],
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
            "has_search": bool(search_query),
            "search_query": search_query,
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
        
        statuses = {status["id"]: status["name"] for status in settings["statuses"]}
        priorities = {priority["id"]: priority["name"] for priority in settings["priorities"]}
        task_types = {task_type["id"]: task_type["name"] for task_type in settings["task_types"]}
    
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
        filter_parts.append(f"Дедлайн от: {filters_copy['deadline_from']}")
    
    if 'deadline_to' in filters_copy:
        filter_parts.append(f"Дедлайн до: {filters_copy['deadline_to']}")
    
    if 'is_completed' in filters_copy:
        completed_status = "Завершенные" if filters_copy['is_completed'] else "Незавершенные"
        filter_parts.append(f"Статус: {completed_status}")
    
    return ", ".join(filter_parts)

def get_sort_name_display(sort_by: str) -> str:
    """Возвращает отображаемое имя поля сортировки"""
    sort_names = {
        "title": "Название",
        "created_at": "Дата создания",
        "deadline": "Дедлайн",
        "priority": "Приоритет",
        "status": "Статус",
        "type": "Тип"
    }
    return sort_names.get(sort_by, sort_by)

# Обработчики событий
async def on_page_prev(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик перехода на предыдущую страницу"""
    # Просто уменьшаем номер страницы, но не меньше 1
    page = manager.dialog_data.get("page", 1)
    if page > 1:
        manager.dialog_data["page"] = page - 1
    await manager.update(data={})

async def on_page_next(c: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик перехода на следующую страницу"""
    # Просто увеличиваем номер страницы, проверка на максимальное количество страниц
    # будет выполнена в getter-функции
    page = manager.dialog_data.get("page", 1)
    manager.dialog_data["page"] = page + 1
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
    search_query = message.text.strip()
    filters = manager.dialog_data.get("filters", {})
    filters["search"] = search_query
    manager.dialog_data["filters"] = filters
    await manager.switch_to(TaskListStates.main)

async def on_page_selected(c: CallbackQuery, button: Any, manager: DialogManager, page: int):
    """Обработчик выбора страницы в NumberedPager"""
    manager.dialog_data["page"] = page
    await manager.update(data={})

# Создаем диалог для списка задач
task_list_dialog = Dialog(
    # Основной экран со списком задач
    Window(
        # Заголовок с информацией о странице и общем количестве задач
        Format("Ваши задачи (страница {page}/{total_pages}, всего {total_tasks}):\n"),
        
        # Сообщение об ошибке, если она возникла
        Format("❌ Ошибка: {error}\n", when=has_error),
        
        # Информация о фильтрах, если они есть
        Format("{filter_description}\n", when=has_filters_and_description),
        
        # Информация о поисковом запросе, если он есть
        Format("Поиск: '{search_query}'\n", when=has_search_and_query),
        
        # Информация о сортировке, если она есть
        Format("Сортировка: {sort_description}\n", when=has_sort_and_description),
        
        # Список задач с использованием виджета List
        List(
            Format(
                "📌 {item[title]} (ID: {item[id]})\n"
                "Описание: {item[description]}\n"
                "Тип: {item[type]}\n"
                "Статус: {item[status]}\n"
                "Приоритет: {item[priority]}\n"
                "Дедлайн: {item[deadline]}\n"
                "Завершена: {item[completed]}\n"
            ),
            items="tasks",
            id="tasks_list",
            page_size=3,
            when=has_tasks
        ),
        
        # Сообщение, если задач нет
        Format("У вас нет задач\n\nСоздайте новую задачу с помощью команды /add_task", when=has_no_tasks),
        
        # Создаем StubScroll для управления пагинацией
        StubScroll(
            id="tasks_scroll",
            pages=lambda data: data.get("total_pages", 1)
        ),
        
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
        
        # Кнопки действий
        Row(
            SwitchTo(Const("🔍 Фильтр"), id="to_filter", state=TaskListStates.filter_menu),
            SwitchTo(Const("🔎 Поиск"), id="to_search", state=TaskListStates.search),
            SwitchTo(Const("📊 Сортировка"), id="to_sort", state=TaskListStates.sort),
        ),
        
        # Кнопки сброса фильтров и сортировки
        Row(
            Button(Const("❌ Сбросить фильтры"), id="reset_filters", on_click=on_reset_filters, when=has_filters),
            Button(Const("❌ Сбросить сортировку"), id="reset_sort", on_click=on_reset_sort, when=has_sort),
        ),
        
        # Кнопка закрытия диалога
        Row(
            Cancel(Const("Закрыть")),
        ),
        
        state=TaskListStates.main,
        getter=get_tasks_data,
    ),
    
    # Экран выбора типа фильтра
    Window(
        Const("Выберите тип фильтра:"),
        Row(
            SwitchTo(Const("🔄 Статус"), id="to_status", state=TaskListStates.filter_status),
            SwitchTo(Const("🔥 Приоритет"), id="to_priority", state=TaskListStates.filter_priority),
        ),
        Row(
            SwitchTo(Const("📋 Тип задачи"), id="to_type", state=TaskListStates.filter_type),
            SwitchTo(Const("📅 Дедлайн"), id="to_deadline", state=TaskListStates.filter_deadline),
        ),
        Row(
            SwitchTo(Const("✅ Показать завершенные"), id="to_completed", state=TaskListStates.filter_completed),
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.filter_menu,
    ),
    
    # Экран фильтра по статусу
    Window(
        Const("Выберите статус для фильтрации:"),
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
            SwitchTo(Const("↩️ Назад"), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_status,
        getter=get_statuses,
    ),
    
    # Экран фильтра по приоритету
    Window(
        Const("Выберите приоритет для фильтрации:"),
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
            SwitchTo(Const("↩️ Назад"), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_priority,
        getter=get_priorities,
    ),
    
    # Экран фильтра по типу задачи
    Window(
        Const("Выберите тип задачи для фильтрации:"),
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
            SwitchTo(Const("↩️ Назад"), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_type,
        getter=get_task_types,
    ),
    
    # Экран фильтра по дедлайну
    Window(
        Const("Выберите период дедлайна для фильтрации:"),
        Row(
            Button(Const("Сегодня"), id="deadline_today", on_click=on_deadline_today),
            Button(Const("Завтра"), id="deadline_tomorrow", on_click=on_deadline_tomorrow),
        ),
        Row(
            Button(Const("Эта неделя"), id="deadline_week", on_click=on_deadline_week),
            Button(Const("Этот месяц"), id="deadline_month", on_click=on_deadline_month),
        ),
        Row(
            Button(Const("Просроченные"), id="deadline_overdue", on_click=on_deadline_overdue),
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_deadline,
    ),
    
    # Экран фильтра по завершенности
    Window(
        Const("Выберите фильтр по завершенности:"),
        Row(
            Button(Const("Показать все задачи"), id="completed_all", on_click=on_completed_all),
        ),
        Row(
            Button(Const("Только незавершенные"), id="uncompleted_only", on_click=on_uncompleted_only),
        ),
        Row(
            Button(Const("Только завершенные"), id="completed_only", on_click=on_completed_only),
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="back_to_filter", state=TaskListStates.filter_menu),
        ),
        state=TaskListStates.filter_completed,
    ),
    
    # Экран сортировки
    Window(
        Const("Выберите параметр сортировки:"),
        Row(
            Button(Const("По названию"), id="sort_title", on_click=on_sort_by_title),
            Button(Const("По дедлайну"), id="sort_deadline", on_click=on_sort_by_deadline),
        ),
        Row(
            Button(Const("По приоритету"), id="sort_priority", on_click=on_sort_by_priority),
            Button(Const("По дате создания"), id="sort_created", on_click=on_sort_by_created),
        ),
        Row(
            Button(Const("По возрастанию"), id="sort_asc", on_click=on_sort_asc),
            Button(Const("По убыванию"), id="sort_desc", on_click=on_sort_desc),
        ),
        Row(
            SwitchTo(Const("↩️ Назад"), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.sort,
    ),
    
    # Экран поиска
    Window(
        Const("Введите поисковый запрос:"),
        TextInput(id="search_query", on_success=SimpleEventProcessor(on_search_query_input)),
        Row(
            SwitchTo(Const("↩️ Отмена"), id="back_to_main", state=TaskListStates.main),
        ),
        state=TaskListStates.search,
    ),
) 