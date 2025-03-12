import logging
import time
import json
import os
import jwt
import uuid
import base64
from datetime import datetime, timedelta, UTC
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram.fsm.state import State, StatesGroup
import re
from aiogram.fsm.context import FSMContext

from backend.database import get_session, create_user_settings
from backend.locale_config import i18n
from backend.services.task_service import TaskService
from backend.services.auth_service import AuthService
from backend.services.settings_service import SettingsService
from backend.dialogs.task_dialogs import TaskDialog
from backend.load_env import env_config

logger = logging.getLogger(__name__)

# Путь к файлу с состояниями авторизации
AUTH_STATES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'auth_states.json')

# Время жизни состояния авторизации в секундах (10 минут)
AUTH_STATE_TTL = 600

# Определяем состояния для поиска задач
class SearchStates(StatesGroup):
    waiting_for_query = State()

# Функция для создания access token
def create_custom_access_token(identity):
    """Создает JWT access token"""
    # Токен действителен 1 час (3600 секунд), как указано в настройках Flask JWT Extended
    expires = datetime.now(UTC) + timedelta(seconds=3600)
    
    # Создаем payload с полями, которые ожидает Flask JWT Extended
    payload = {
        'sub': identity,  # Идентификатор пользователя
        'exp': int(expires.timestamp()),  # Время истечения токена в формате timestamp
        'iat': int(datetime.now(UTC).timestamp()),  # Время создания токена
        'nbf': int(datetime.now(UTC).timestamp()),  # Время, с которого токен действителен
        'jti': str(uuid.uuid4()),  # Уникальный идентификатор токена
        'type': 'access',  # Тип токена
        'fresh': False  # Токен не является "свежим"
    }
    
    return jwt.encode(payload, env_config.get('JWT_SECRET_KEY'), algorithm='HS256')

# Функция для создания refresh token
def create_custom_refresh_token(identity):
    """Создает JWT refresh token"""
    # Токен действителен 30 дней (2592000 секунд), как указано в настройках Flask JWT Extended
    expires = datetime.now(UTC) + timedelta(seconds=2592000)
    
    # Создаем payload с полями, которые ожидает Flask JWT Extended
    payload = {
        'sub': identity,  # Идентификатор пользователя
        'exp': int(expires.timestamp()),  # Время истечения токена в формате timestamp
        'iat': int(datetime.now(UTC).timestamp()),  # Время создания токена
        'nbf': int(datetime.now(UTC).timestamp()),  # Время, с которого токен действителен
        'jti': str(uuid.uuid4()),  # Уникальный идентификатор токена
        'type': 'refresh'  # Тип токена
    }
    
    return jwt.encode(payload, env_config.get('JWT_SECRET_KEY'), algorithm='HS256')

# Функция для загрузки состояний авторизации из файла
def load_auth_states():
    """Загружает состояния авторизации из файла"""
    if not os.path.exists(AUTH_STATES_FILE):
        return {}
    
    try:
        with open(AUTH_STATES_FILE, 'r') as f:
            auth_states = json.load(f)
        
        # Преобразуем строковые ключи timestamp обратно в числа
        for state, data in auth_states.items():
            auth_states[state] = (data[0], float(data[1]))
        
        return auth_states
    except Exception as e:
        logger.error(f"Ошибка при загрузке состояний авторизации: {e}")
        return {}

# Функция для сохранения состояний авторизации в файл
def save_auth_states(auth_states):
    """Сохраняет состояния авторизации в файл"""
    try:
        with open(AUTH_STATES_FILE, 'w') as f:
            json.dump(auth_states, f)
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояний авторизации: {e}")

# Функция для добавления состояния авторизации
def add_auth_state(state, redirect_url):
    """Добавляет состояние авторизации"""
    auth_states = load_auth_states()
    auth_states[state] = (redirect_url, time.time())
    save_auth_states(auth_states)

# Функция для получения и удаления состояния авторизации
def get_and_remove_auth_state(state):
    """Получает и удаляет состояние авторизации"""
    auth_states = load_auth_states()
    if state in auth_states:
        redirect_url, timestamp = auth_states.pop(state)
        save_auth_states(auth_states)
        
        # Проверяем, не истекло ли состояние
        if time.time() - timestamp <= AUTH_STATE_TTL:
            return redirect_url
    
    return None

# Функция для очистки старых состояний авторизации
def cleanup_auth_states():
    """Очищает старые состояния авторизации"""
    auth_states = load_auth_states()
    current_time = time.time()
    expired_states = []
    
    for state, (_, timestamp) in auth_states.items():
        if current_time - timestamp > AUTH_STATE_TTL:
            expired_states.append(state)
    
    if expired_states:
        for state in expired_states:
            auth_states.pop(state)
        save_auth_states(auth_states)

router = Router()


@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start, создает нового пользователя"""
    # Очищаем старые состояния авторизации
    cleanup_auth_states()
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Проверяем, есть ли параметр авторизации
    auth_state = None
    if message.text and len(message.text.split()) > 1:
        param = message.text.split()[1]
        # Проверяем, начинается ли параметр с auth_
        if param.startswith('auth_'):
            auth_state = param[5:]  # Убираем префикс auth_
            logger.debug(f"Получен параметр авторизации: {auth_state}")
        else:
            auth_state = param
            logger.debug(f"Получен параметр: {param}")
    
    logger.debug(f"Команда /start от пользователя {user_id} ({username})")
    
    async with get_session() as session:
        auth_service = AuthService(session)
        # Проверяем, существует ли пользователь
        user = await auth_service.get_user_by_id(str(user_id))
        
        if not user:
            # Создаем нового пользователя
            logger.debug(f"Создаем нового пользователя {user_id} ({username})")
            user = await auth_service.create_user(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            # Создаем настройки для нового пользователя
            try:
                await create_user_settings(user.telegram_id, session)
                logger.debug(f"Настройки для пользователя {user_id} созданы успешно")
            except Exception as e:
                logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
            
            logger.debug(f"Создан новый пользователь: {user_id} ({username})")
        else:
            logger.debug(f"Пользователь {user_id} уже существует")
            # Проверяем, есть ли у пользователя настройки
            settings_service = SettingsService(session)
            statuses = await settings_service.get_statuses(str(user_id))
            if not statuses:
                logger.debug(f"У пользователя {user_id} нет настроек, создаем их")
                try:
                    await create_user_settings(user.telegram_id, session)
                    logger.debug(f"Настройки для пользователя {user_id} созданы успешно")
                except Exception as e:
                    logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
    
    # Если есть параметр авторизации, генерируем токены и отправляем ссылку для входа
    if auth_state:
        # Получаем URL для редиректа
        redirect_url = get_and_remove_auth_state(auth_state)
        
        if redirect_url:
            # Проверяем URL и заменяем localhost на публичный домен для Telegram
            if "localhost" in redirect_url:
                # Telegram не принимает URL с localhost, заменяем на публичный домен
                # В продакшене нужно использовать реальный домен
                public_url = env_config.get('PUBLIC_URL')
                redirect_url = redirect_url.replace("http://localhost:3000", public_url)
                logger.debug(f"Заменен localhost URL на публичный домен: {redirect_url}")
            
            # Создаем токены с помощью собственных функций
            access_token = create_custom_access_token(str(user_id))
            refresh_token = create_custom_refresh_token(str(user_id))
            
            # Логируем URL для редиректа и токены
            logger.debug(f"Redirect URL: {redirect_url}")
            logger.debug(f"Access token created")
            logger.debug(f"Refresh token created")
            
            # Формируем прямую ссылку на веб-приложение с токенами
            auth_url = f"{redirect_url}?access_token={access_token}&refresh_token={refresh_token}&user_id={user_id}"
            
            # Логируем URL для авторизации
            logger.debug(f"Auth URL created: {auth_url}")
            
            # Создаем клавиатуру с кнопкой для входа
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=i18n.format_value("login-to-web"),
                    url=auth_url
                )]
            ])
            
            # Создаем клавиатуру с кнопкой для входа через Mini App
            mini_app_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=i18n.format_value("login-to-web-mini-app"),
                    web_app={"url": auth_url}
                )]
            ])
            
            # Отправляем сообщение с кнопкой для входа
            await message.answer(
                i18n.format_value("web-auth-success"),
                reply_markup=keyboard
            )
            
            # Отправляем сообщение с кнопкой для входа через Mini App
            await message.answer(
                i18n.format_value("web-auth-mini-app"),
                reply_markup=mini_app_keyboard
            )
        else:
            logger.error(f"Не найдено состояние авторизации для {auth_state}")
            await message.answer(i18n.format_value("web-auth-error"))
    else:
        # Отправляем приветственное сообщение
        await message.answer(
            i18n.format_value(
                "welcome-message",
                {"name": first_name or username or ""}
            )
        )
        # Отправляем сообщение с помощью
        await show_help(message)

@router.message(Command("stop"))
async def stop_command(message: Message):
    await message.answer(i18n.format_value("stopped"))

# Функция для отображения справки
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

@router.message(Command("help"))
async def help_command(message: Message):
    """Показать справку по командам"""
    await show_help(message)

@router.message(Command("tasks"))
async def list_tasks(message: Message):
    """Показать список задач с пагинацией"""
    await show_tasks_page(message.from_user.id, message, page=1)

async def show_tasks_page(user_id, message: Message, page: int = 1, filters: dict = None, sort_by: str = None, sort_order: str = "asc"):
    """Показывает страницу с задачами пользователя"""
    if filters is None:
        filters = {}
    
    if not user_id:
        logger.error("Не удалось получить ID пользователя из сообщения")
        return
        
    page_size = 3  # Количество задач на странице
    
    # Извлекаем поисковый запрос из фильтров, если он есть
    search_query = filters.get('search', '')
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        # Метод возвращает кортеж (tasks, total_tasks), а не словарь
        tasks, total_tasks = await task_service.get_tasks_paginated(
            user_id,
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            search_query=search_query
        )
        
        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
        
        # Если запрошенная страница больше общего количества страниц, показываем последнюю страницу
        if page > total_pages and total_pages > 0:
            page = total_pages
            # Получаем задачи для последней страницы
            tasks, _ = await task_service.get_tasks_paginated(
                user_id,
                page=page,
                page_size=page_size,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                search_query=search_query
            )
        
        # Формируем текст сообщения
        if total_tasks == 0:
            response = "У вас нет задач"
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f" с фильтрами: {filter_description}"
            if search_query:
                response += f"\nПоиск: '{search_query}'"
            response += "\n\nСоздайте новую задачу с помощью команды /add_task"
        else:
            # Формируем заголовок с информацией о странице и фильтрах
            response = f"Ваши задачи (страница {page}/{total_pages}, всего {total_tasks}):\n"
            
            # Добавляем информацию о фильтрах, если они есть
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f"Фильтры: {filter_description}\n"
            
            # Добавляем информацию о поисковом запросе, если он есть
            if search_query:
                response += f"Поиск: '{search_query}'\n"
            
            # Добавляем информацию о сортировке, если она есть
            if sort_by:
                sort_name = get_sort_name_display(sort_by)
                sort_direction = "по возрастанию" if sort_order == "asc" else "по убыванию"
                response += f"Сортировка: {sort_name} {sort_direction}\n"
            
            response += "\n"
            
            # Добавляем информацию о задачах
            for task in tasks:
                response += i18n.format_value("task-item", {
                    "id": task['id'],
                    "title": task['title']
                }) + "\n"

                if task['description']:
                    response += i18n.format_value("task-description-line", {
                        "description": task['description']
                    }) + "\n"

                if task['status']:
                    response += i18n.format_value("task-status-line", {
                        "status": task['status']['name']
                    }) + "\n"

                if task['priority']:
                    response += i18n.format_value("task-priority-line", {
                        "priority": task['priority']['name']
                    }) + "\n"
                    
                if task['deadline']:
                    response += i18n.format_value("task-deadline-line", {
                        "deadline": task['deadline']
                    }) + "\n"
                    
                response += "\n"
        
        # Создаем клавиатуру для навигации
        keyboard = []
        
        # Кнопки для навигации по страницам
        navigation_row = []
        
        # Кнопка "Предыдущая страница"
        if page > 1:
            # Кодируем фильтры и параметры сортировки в callback_data
            encoded_filters = encode_filters(filters)
            callback_data = f"tasks_page_{page-1}_{encoded_filters}"
            
            if sort_by:
                callback_data += f"_{sort_by}_{sort_order}"
            else:
                callback_data += "__"
                
            navigation_row.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=callback_data
            ))
        
        # Кнопка "Следующая страница"
        if page < total_pages:
            # Кодируем фильтры и параметры сортировки в callback_data
            encoded_filters = encode_filters(filters)
            callback_data = f"tasks_page_{page+1}_{encoded_filters}"
            
            if sort_by:
                callback_data += f"_{sort_by}_{sort_order}"
            else:
                callback_data += "__"
                
            navigation_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=callback_data
            ))
        
        if navigation_row:
            keyboard.append(navigation_row)
        
        # Кнопки для фильтрации и сортировки
        action_row = []
        
        # Кнопка фильтрации
        action_row.append(InlineKeyboardButton(
            text="🔍 Фильтр",
            callback_data="tasks_filter"
        ))
        
        # Кнопка поиска
        # Кодируем текущие фильтры и параметры сортировки в callback_data
        encoded_filters = encode_filters(filters)
        search_callback_data = f"tasks_search_{encoded_filters}"
        
        if sort_by:
            search_callback_data += f"_{sort_by}_{sort_order}"
        else:
            search_callback_data += "__"
            
        action_row.append(InlineKeyboardButton(
            text="🔎 Поиск",
            callback_data=search_callback_data
        ))
        
        # Кнопка сортировки
        action_row.append(InlineKeyboardButton(
            text="📊 Сортировка",
            callback_data="tasks_sort"
        ))
        
        keyboard.append(action_row)
        
        # Добавляем кнопку сброса фильтров и сортировки, если они применены
        if filters or sort_by:
            reset_row = []
            
            if filters:
                reset_row.append(InlineKeyboardButton(
                    text="❌ Сбросить фильтры",
                    callback_data="tasks_reset_filters"
                ))
            
            if sort_by:
                reset_row.append(InlineKeyboardButton(
                    text="❌ Сбросить сортировку",
                    callback_data="tasks_reset_sort"
                ))
            
            keyboard.append(reset_row)
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с задачами и клавиатурой
        await message.answer(response, reply_markup=markup)

# Функции для кодирования и декодирования фильтров
def encode_filters(filters: dict) -> str:
    """Кодирует фильтры в строку для использования в callback_data"""
    if not filters:
        return ""
    
    # Создаем более компактное представление фильтров
    compact_filters = {}
    
    # Используем короткие ключи для уменьшения размера
    key_mapping = {
        'status_id': 's',
        'priority_id': 'p',
        'type_id': 't',
        'duration_id': 'd',
        'deadline_from': 'df',
        'deadline_to': 'dt',
        'search': 'q'
    }
    
    # Преобразуем даты в более короткий формат (YYMMDD)
    for key, value in filters.items():
        if key in key_mapping:
            # Для дат используем более короткий формат
            if key in ['deadline_from', 'deadline_to'] and value:
                try:
                    # Предполагаем, что значение в формате YYYY-MM-DD
                    date_parts = value.split('-')
                    if len(date_parts) == 3:
                        # Преобразуем в формат YYMMDD
                        year = date_parts[0][2:]  # Берем только последние 2 цифры года
                        month = date_parts[1]
                        day = date_parts[2]
                        compact_filters[key_mapping[key]] = f"{year}{month}{day}"
                    else:
                        compact_filters[key_mapping[key]] = value
                except Exception as e:
                    logger.error(f"Ошибка при преобразовании даты {value}: {e}")
                    compact_filters[key_mapping[key]] = value
            else:
                compact_filters[key_mapping[key]] = value
        else:
            compact_filters[key] = value
    
    # Преобразуем словарь в JSON-строку
    json_str = json.dumps(compact_filters, separators=(',', ':'))
    
    # Кодируем в base64 для безопасной передачи в callback_data
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    
    # Если размер все еще слишком большой, обрезаем некоторые данные
    if len(encoded) > 60:  # Оставляем небольшой запас до лимита в 64 байта
        logger.warning(f"Encoded filters too large: {len(encoded)} bytes")
        # Оставляем только самые важные фильтры
        essential_filters = {k: v for k, v in compact_filters.items() if k in ['s', 'p', 't']}
        json_str = json.dumps(essential_filters, separators=(',', ':'))
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
    
    return encoded

def decode_filters(encoded: str) -> dict:
    """Декодирует строку в словарь фильтров"""
    if not encoded:
        return {}
    
    try:
        # Декодируем из base64
        json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
        
        # Преобразуем JSON-строку в словарь
        compact_filters = json.loads(json_str)
        
        # Преобразуем короткие ключи обратно в полные
        key_mapping = {
            's': 'status_id',
            'p': 'priority_id',
            't': 'type_id',
            'd': 'duration_id',
            'df': 'deadline_from',
            'dt': 'deadline_to',
            'q': 'search'
        }
        
        filters = {}
        for key, value in compact_filters.items():
            if key in key_mapping:
                # Для дат преобразуем обратно в формат YYYY-MM-DD
                if key in ['df', 'dt'] and value and len(value) == 6:
                    try:
                        # Предполагаем, что значение в формате YYMMDD
                        year = "20" + value[:2]  # Добавляем "20" к году
                        month = value[2:4]
                        day = value[4:6]
                        filters[key_mapping[key]] = f"{year}-{month}-{day}"
                    except Exception as e:
                        logger.error(f"Ошибка при преобразовании даты {value}: {e}")
                        filters[key_mapping[key]] = value
                else:
                    filters[key_mapping[key]] = value
            else:
                filters[key] = value
        
        return filters
    except Exception as e:
        logger.error(f"Ошибка при декодировании фильтров: {e}")
        return {}

# Обработчик нажатия на кнопки пагинации
@router.callback_query(F.data.startswith("tasks_page_"))
async def on_tasks_page_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопки пагинации"""
    # Извлекаем номер страницы и фильтры из callback_data
    parts = callback_query.data.split("_", 3)
    page = int(parts[2])
    
    # Проверяем, есть ли фильтры и параметры сортировки
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    if len(parts) > 3:
        # Формат: tasks_page_1_encoded_filters_sort_by_sort_order
        remaining_parts = parts[3].split("_")
        
        if len(remaining_parts) >= 1 and remaining_parts[0]:
            filters = decode_filters(remaining_parts[0])
        
        if len(remaining_parts) >= 2 and remaining_parts[1]:
            sort_by = remaining_parts[1]
        
        if len(remaining_parts) >= 3 and remaining_parts[2]:
            sort_order = remaining_parts[2]
    
    logger.debug(f"Получен колбэк для перехода на страницу {page}, фильтры: {filters}, сортировка: {sort_by} {sort_order}")
    
    # Извлекаем поисковый запрос из фильтров, если он есть
    search_query = filters.get('search', '')
    
    user_id = callback_query.message.from_user.id
    page_size = 3  # Количество задач на странице
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        tasks, total_tasks = await task_service.get_tasks_paginated(
            str(user_id),
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            search_query=search_query
        )
        
        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
        
        # Если запрошенная страница больше общего количества страниц, показываем последнюю страницу
        if page > total_pages and total_pages > 0:
            page = total_pages
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
        
        # Формируем текст сообщения
        if total_tasks == 0:
            response = "У вас нет задач"
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f" с фильтрами: {filter_description}"
            if search_query:
                response += f"\nПоиск: '{search_query}'"
            response += "\n\nСоздайте новую задачу с помощью команды /add_task"
        else:
            # Формируем заголовок с информацией о странице и фильтрах
            response = f"Ваши задачи (страница {page}/{total_pages}, всего {total_tasks}):\n"
            
            # Добавляем информацию о фильтрах, если они есть
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f"Фильтры: {filter_description}\n"
            
            # Добавляем информацию о поисковом запросе, если он есть
            if search_query:
                response += f"Поиск: '{search_query}'\n"
            
            # Добавляем информацию о сортировке, если она есть
            if sort_by:
                sort_name = get_sort_name_display(sort_by)
                sort_direction = "по возрастанию" if sort_order == "asc" else "по убыванию"
                response += f"Сортировка: {sort_name} {sort_direction}\n"
            
            response += "\n"
            
            # Добавляем информацию о задачах
            for task in tasks:
                response += i18n.format_value("task-item", {
                    "id": task['id'],
                    "title": task['title']
                }) + "\n"

                if task['description']:
                    response += i18n.format_value("task-description-line", {
                        "description": task['description']
                    }) + "\n"

                if task['status']:
                    response += i18n.format_value("task-status-line", {
                        "status": task['status']['name']
                    }) + "\n"

                if task['priority']:
                    response += i18n.format_value("task-priority-line", {
                        "priority": task['priority']['name']
                    }) + "\n"
                    
                if task['deadline']:
                    response += i18n.format_value("task-deadline-line", {
                        "deadline": task['deadline']
                    }) + "\n"
                    
                response += "\n"
        
        # Создаем клавиатуру для навигации
        keyboard = []
        
        # Кнопки для навигации по страницам
        navigation_row = []
        
        # Кнопка "Предыдущая страница"
        if page > 1:
            # Кодируем фильтры и параметры сортировки в callback_data
            encoded_filters = encode_filters(filters)
            callback_data = f"tasks_page_{page-1}_{encoded_filters}"
            
            if sort_by:
                callback_data += f"_{sort_by}_{sort_order}"
            else:
                callback_data += "__"
                
            navigation_row.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=callback_data
            ))
        
        # Кнопка "Следующая страница"
        if page < total_pages:
            # Кодируем фильтры и параметры сортировки в callback_data
            encoded_filters = encode_filters(filters)
            callback_data = f"tasks_page_{page+1}_{encoded_filters}"
            
            if sort_by:
                callback_data += f"_{sort_by}_{sort_order}"
            else:
                callback_data += "__"
                
            navigation_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=callback_data
            ))
        
        if navigation_row:
            keyboard.append(navigation_row)
        
        # Кнопки для фильтрации и сортировки
        action_row = []
        
        # Кнопка фильтрации
        action_row.append(InlineKeyboardButton(
            text="🔍 Фильтр",
            callback_data="tasks_filter"
        ))
        
        # Кнопка поиска
        # Кодируем текущие фильтры и параметры сортировки в callback_data
        encoded_filters = encode_filters(filters)
        search_callback_data = f"tasks_search_{encoded_filters}"
        
        if sort_by:
            search_callback_data += f"_{sort_by}_{sort_order}"
        else:
            search_callback_data += "__"
            
        action_row.append(InlineKeyboardButton(
            text="🔎 Поиск",
            callback_data=search_callback_data
        ))
        
        # Кнопка сортировки
        action_row.append(InlineKeyboardButton(
            text="📊 Сортировка",
            callback_data="tasks_sort"
        ))
        
        keyboard.append(action_row)
        
        # Добавляем кнопку сброса фильтров и сортировки, если они применены
        if filters or sort_by:
            reset_row = []
            
            if filters:
                reset_row.append(InlineKeyboardButton(
                    text="❌ Сбросить фильтры",
                    callback_data="tasks_reset_filters"
                ))
            
            if sort_by:
                reset_row.append(InlineKeyboardButton(
                    text="❌ Сбросить сортировку",
                    callback_data="tasks_reset_sort"
                ))
            
            keyboard.append(reset_row)
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем или редактируем сообщение
        await callback_query.message.edit_text(response, reply_markup=markup)
        await callback_query.answer()

# Обработчик нажатия на кнопку сброса всех фильтров
@router.callback_query(F.data.startswith("tasks_filter_reset"))
async def on_tasks_filter_reset_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку сброса всех фильтров"""
    logger.debug("Получен колбэк для сброса всех фильтров")
    
    # Проверяем, есть ли параметры сортировки
    sort_by = None
    sort_order = "asc"
    
    parts = callback_query.data.split("_", 3)
    if len(parts) > 3:
        # Формат: tasks_filter_reset_sort_by_sort_order
        remaining_parts = parts[3].split("_")
        
        if len(remaining_parts) >= 1 and remaining_parts[0]:
            sort_by = remaining_parts[0]
        
        if len(remaining_parts) >= 2 and remaining_parts[1]:
            sort_order = remaining_parts[1]
    
    # Показываем первую страницу без фильтров, но с сохранением сортировки
    user_id = callback_query.message.from_user.id
    page_size = 3  # Количество задач на странице
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        tasks, total_tasks = await task_service.get_tasks_paginated(
            str(user_id),
            page=1,
            page_size=page_size,
            filters={},
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
        
        # Формируем текст сообщения
        if total_tasks == 0:
            response = "У вас нет задач"
            response += "\n\nСоздайте новую задачу с помощью команды /add_task"
        else:
            # Формируем заголовок с информацией о странице и фильтрах
            response = f"Ваши задачи (страница 1/{total_pages}, всего {total_tasks}):\n"
            
            # Добавляем информацию о сортировке, если она есть
            if sort_by:
                sort_name = get_sort_name_display(sort_by)
                sort_direction = "по возрастанию" if sort_order == "asc" else "по убыванию"
                response += f"Сортировка: {sort_name} {sort_direction}\n"
            
            response += "\n"
            
            # Добавляем информацию о задачах
            for task in tasks:
                response += i18n.format_value("task-item", {
                    "id": task['id'],
                    "title": task['title']
                }) + "\n"

                if task['description']:
                    response += i18n.format_value("task-description-line", {
                        "description": task['description']
                    }) + "\n"

                if task['status']:
                    response += i18n.format_value("task-status-line", {
                        "status": task['status']['name']
                    }) + "\n"

                if task['priority']:
                    response += i18n.format_value("task-priority-line", {
                        "priority": task['priority']['name']
                    }) + "\n"
                    
                if task['deadline']:
                    response += i18n.format_value("task-deadline-line", {
                        "deadline": task['deadline']
                    }) + "\n"
                    
                response += "\n"
        
        # Создаем клавиатуру для навигации
        keyboard = []
        
        # Кнопки для навигации по страницам
        navigation_row = []
        
        # Кнопка "Следующая страница"
        if total_pages > 1:
            # Кодируем параметры сортировки в callback_data
            callback_data = f"tasks_page_2_"
            
            if sort_by:
                callback_data += f"_{sort_by}_{sort_order}"
            else:
                callback_data += "__"
                
            navigation_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=callback_data
            ))
        
        if navigation_row:
            keyboard.append(navigation_row)
        
        # Кнопки для фильтрации и сортировки
        action_row = []
        
        # Кнопка фильтрации
        action_row.append(InlineKeyboardButton(
            text="🔍 Фильтр",
            callback_data="tasks_filter"
        ))
        
        # Кнопка поиска
        action_row.append(InlineKeyboardButton(
            text="🔎 Поиск",
            callback_data="tasks_search___"
        ))
        
        # Кнопка сортировки
        action_row.append(InlineKeyboardButton(
            text="📊 Сортировка",
            callback_data="tasks_sort"
        ))
        
        keyboard.append(action_row)
        
        # Добавляем кнопку сброса сортировки, если она применена
        if sort_by:
            keyboard.append([InlineKeyboardButton(
                text="❌ Сбросить сортировку",
                callback_data="tasks_reset_sort"
            )])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем или редактируем сообщение
        await callback_query.message.edit_text(response, reply_markup=markup)
        await callback_query.answer("Фильтры сброшены")

# Обработчик нажатия на кнопку сброса сортировки
@router.callback_query(F.data.startswith("tasks_sort_reset"))
async def on_tasks_sort_reset_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку сброса сортировки"""
    logger.debug("Получен колбэк для сброса сортировки")
    
    # Проверяем, есть ли фильтры
    filters = {}
    
    parts = callback_query.data.split("_", 3)
    if len(parts) > 3:
        # Формат: tasks_sort_reset_encoded_filters
        filters = decode_filters(parts[3])
    
    # Показываем первую страницу с фильтрами, но без сортировки
    user_id = callback_query.message.from_user.id
    page_size = 3  # Количество задач на странице
    
    # Извлекаем поисковый запрос из фильтров, если он есть
    search_query = filters.get('search', '')
    
    async with get_session() as session:
        task_service = TaskService(session)
        
        # Получаем задачи с пагинацией и общее количество
        tasks, total_tasks = await task_service.get_tasks_paginated(
            str(user_id),
            page=1,
            page_size=page_size,
            filters=filters,
            search_query=search_query
        )
        
        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
        
        # Формируем текст сообщения
        if total_tasks == 0:
            response = "У вас нет задач"
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f" с фильтрами: {filter_description}"
            if search_query:
                response += f"\nПоиск: '{search_query}'"
            response += "\n\nСоздайте новую задачу с помощью команды /add_task"
        else:
            # Формируем заголовок с информацией о странице и фильтрах
            response = f"Ваши задачи (страница 1/{total_pages}, всего {total_tasks}):\n"
            
            # Добавляем информацию о фильтрах, если они есть
            if filters:
                filter_description = get_filter_description(filters)
                if filter_description:
                    response += f"Фильтры: {filter_description}\n"
            
            # Добавляем информацию о поисковом запросе, если он есть
            if search_query:
                response += f"Поиск: '{search_query}'\n"
            
            response += "\n"
            
            # Добавляем информацию о задачах
            for task in tasks:
                response += i18n.format_value("task-item", {
                    "id": task['id'],
                    "title": task['title']
                }) + "\n"

                if task['description']:
                    response += i18n.format_value("task-description-line", {
                        "description": task['description']
                    }) + "\n"

                if task['status']:
                    response += i18n.format_value("task-status-line", {
                        "status": task['status']['name']
                    }) + "\n"

                if task['priority']:
                    response += i18n.format_value("task-priority-line", {
                        "priority": task['priority']['name']
                    }) + "\n"
                    
                if task['deadline']:
                    response += i18n.format_value("task-deadline-line", {
                        "deadline": task['deadline']
                    }) + "\n"
                    
                response += "\n"
        
        # Создаем клавиатуру для навигации
        keyboard = []
        
        # Кнопки для навигации по страницам
        navigation_row = []
        
        # Кнопка "Следующая страница"
        if total_pages > 1:
            # Кодируем фильтры в callback_data
            encoded_filters = encode_filters(filters)
            callback_data = f"tasks_page_2_{encoded_filters}__"
                
            navigation_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=callback_data
            ))
        
        if navigation_row:
            keyboard.append(navigation_row)
        
        # Кнопки для фильтрации и сортировки
        action_row = []
        
        # Кнопка фильтрации
        action_row.append(InlineKeyboardButton(
            text="🔍 Фильтр",
            callback_data="tasks_filter"
        ))
        
        # Кнопка поиска
        # Кодируем текущие фильтры в callback_data
        encoded_filters = encode_filters(filters)
        search_callback_data = f"tasks_search_{encoded_filters}__"
            
        action_row.append(InlineKeyboardButton(
            text="🔎 Поиск",
            callback_data=search_callback_data
        ))
        
        # Кнопка сортировки
        action_row.append(InlineKeyboardButton(
            text="📊 Сортировка",
            callback_data="tasks_sort"
        ))
        
        keyboard.append(action_row)
        
        # Добавляем кнопку сброса фильтров, если они применены
        if filters:
            keyboard.append([InlineKeyboardButton(
                text="❌ Сбросить фильтры",
                callback_data="tasks_reset_filters"
            )])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем или редактируем сообщение
        await callback_query.message.edit_text(response, reply_markup=markup)
        await callback_query.answer("Сортировка сброшена")

# Обработчик нажатия на кнопку фильтрации
@router.callback_query(F.data == "tasks_filter")
async def on_filter_button_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку фильтрации"""
    logger.debug("Получен колбэк для выбора фильтра")
    
    # Создаем клавиатуру с кнопками для выбора типа фильтра
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Статус",
                callback_data="tasks_filter_status"
            ),
            InlineKeyboardButton(
                text="🔥 Приоритет",
                callback_data="tasks_filter_priority"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Тип задачи",
                callback_data="tasks_filter_type"
            ),
            InlineKeyboardButton(
                text="📅 Дедлайн",
                callback_data="tasks_filter_deadline"
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="tasks_filter_back"
            )
        ]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем сообщение с клавиатурой для выбора типа фильтра
    await callback_query.message.edit_text(
        "Выберите тип фильтра:",
        reply_markup=markup
    )
    await callback_query.answer()

# Обработчик выбора фильтра по статусу
@router.callback_query(F.data == "tasks_filter_status")
async def on_filter_status_callback(callback_query: CallbackQuery):
    """Обработчик выбора фильтра по статусу"""
    logger.debug("Получен колбэк для фильтрации по статусу")
    
    user_id = callback_query.from_user.id
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(str(user_id))
        
        if not statuses:
            await callback_query.answer("Статусы не найдены")
            return
        
        # Создаем клавиатуру с кнопками для выбора статуса
        keyboard = []
        
        # Группируем кнопки по 2 в ряд
        for i in range(0, len(statuses), 2):
            row = []
            # Добавляем первую кнопку в ряд
            row.append(InlineKeyboardButton(
                text=f"{statuses[i]['name']}",
                callback_data=f"tasks_filter_status_set_{statuses[i]['id']}"
            ))
            
            # Добавляем вторую кнопку, если она есть
            if i + 1 < len(statuses):
                row.append(InlineKeyboardButton(
                    text=f"{statuses[i + 1]['name']}",
                    callback_data=f"tasks_filter_status_set_{statuses[i + 1]['id']}"
                ))
            
            keyboard.append(row)
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="tasks_filter"
        )])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с клавиатурой для выбора статуса
        await callback_query.message.edit_text(
            "Выберите статус задачи:",
            reply_markup=markup
        )
        await callback_query.answer()

# Обработчик установки фильтра по статусу
@router.callback_query(F.data.startswith("tasks_filter_status_set_"))
async def on_filter_status_set_callback(callback_query: CallbackQuery):
    """Обработчик установки фильтра по статусу"""
    logger.debug("Получен колбэк для установки фильтра по статусу")
    
    # Извлекаем ID статуса из callback_data
    status_id = int(callback_query.data.split("_")[-1])
    
    # Извлекаем текущие фильтры из сообщения
    message_text = callback_query.message.text
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Добавляем фильтр по статусу
    filters["status_id"] = status_id
    
    # Показываем первую страницу с примененным фильтром
    await show_tasks_page(callback_query.from_user.id, callback_query.message, page=1, filters=filters, sort_by=sort_by, sort_order=sort_order)
    await callback_query.answer("Фильтр по статусу применен")

# Обработчик нажатия на кнопку сортировки
@router.callback_query(F.data == "tasks_sort")
async def on_sort_button_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку сортировки"""
    logger.debug("Получен колбэк для выбора сортировки")
    
    # Создаем клавиатуру с кнопками для выбора поля сортировки
    keyboard = [
        [
            InlineKeyboardButton(
                text="📝 По названию",
                callback_data="tasks_sort_field_title"
            ),
            InlineKeyboardButton(
                text="⏰ По дедлайну",
                callback_data="tasks_sort_field_deadline"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔥 По приоритету",
                callback_data="tasks_sort_field_priority"
            ),
            InlineKeyboardButton(
                text="🔄 По статусу",
                callback_data="tasks_sort_field_status"
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 По дате создания",
                callback_data="tasks_sort_field_created_at"
            ),
            InlineKeyboardButton(
                text="✅ По дате завершения",
                callback_data="tasks_sort_field_completed_at"
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="tasks_sort_back"
            )
        ]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем сообщение с клавиатурой для выбора поля сортировки
    await callback_query.message.edit_text(
        "Выберите поле для сортировки:",
        reply_markup=markup
    )
    await callback_query.answer()

# Обработчик нажатия на кнопку выбора поля сортировки
@router.callback_query(F.data.startswith("tasks_sort_field_"))
async def on_sort_field_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку выбора поля сортировки"""
    logger.debug("Получен колбэк для выбора направления сортировки")
    
    # Извлекаем поле сортировки из callback_data
    sort_field = callback_query.data.split("_")[-1]
    
    # Создаем клавиатуру с кнопками для выбора направления сортировки
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔼 По возрастанию",
                callback_data=f"tasks_sort_direction_{sort_field}_asc"
            ),
            InlineKeyboardButton(
                text="🔽 По убыванию",
                callback_data=f"tasks_sort_direction_{sort_field}_desc"
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="tasks_sort"
            )
        ]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем сообщение с клавиатурой для выбора направления сортировки
    await callback_query.message.edit_text(
        f"Выберите направление сортировки для поля '{get_sort_name_display(sort_field)}':",
        reply_markup=markup
    )
    await callback_query.answer()

# Функция для получения отображаемого имени поля сортировки
def get_sort_name_display(sort_by: str) -> str:
    """Возвращает название поля сортировки для отображения пользователю"""
    sort_names = {
        "title": "по названию",
        "deadline": "по дедлайну",
        "priority": "по приоритету",
        "status": "по статусу",
        "created_at": "по дате создания",
        "completed_at": "по дате завершения"
    }
    
    return sort_names.get(sort_by, sort_by)

# Обработчик нажатия на кнопку выбора направления сортировки
@router.callback_query(F.data.startswith("tasks_sort_direction_"))
async def on_sort_direction_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку выбора направления сортировки"""
    logger.debug("Получен колбэк для применения сортировки")
    
    # Извлекаем поле и направление сортировки из callback_data
    parts = callback_query.data.split("_")
    sort_field = parts[-2]
    sort_order = parts[-1]
    
    # Извлекаем текущие фильтры из сообщения
    message_text = callback_query.message.text
    filters = {}
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Создаем новое сообщение с правильным user_id
    message = callback_query.message

    # Логируем ID пользователя для отладки
    logger.debug(f"ID пользователя в колбэке: {callback_query.from_user.id}")
    
    # Показываем первую страницу с примененной сортировкой
    await show_tasks_page(callback_query.from_user.id, message, page=1, filters=filters, sort_by=sort_field, sort_order=sort_order)
    await callback_query.answer(f"Сортировка по полю '{get_sort_name_display(sort_field)}' применена")

# Обработчик нажатия на кнопку "Назад" в меню сортировки
@router.callback_query(F.data == "tasks_sort_back")
async def on_sort_back_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку "Назад" в меню сортировки"""
    logger.debug("Получен колбэк для возврата из меню сортировки")
    
    # Извлекаем текущие фильтры, сортировку и страницу из сообщения
    message_text = callback_query.message.text
    page = 1
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    # Извлекаем номер страницы из сообщения
    if "страница" in message_text.lower():
        page_match = re.search(r'страница (\d+)/(\d+)', message_text.lower())
        if page_match:
            page = int(page_match.group(1))
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Показываем страницу с текущими фильтрами и сортировкой
    await show_tasks_page(callback_query.from_user.id, callback_query.message, page=page, filters=filters, sort_by=sort_by, sort_order=sort_order)
    await callback_query.answer()

# Обработчик нажатия на кнопку "Назад" в меню фильтрации
@router.callback_query(F.data == "tasks_filter_back")
async def on_filter_back_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку "Назад" в меню фильтрации"""
    logger.debug("Получен колбэк для возврата из меню фильтрации")
    
    # Извлекаем текущие фильтры, сортировку и страницу из сообщения
    message_text = callback_query.message.text
    page = 1
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    # Извлекаем номер страницы из сообщения
    if "страница" in message_text.lower():
        page_match = re.search(r'страница (\d+)/(\d+)', message_text.lower())
        if page_match:
            page = int(page_match.group(1))
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Показываем страницу с текущими фильтрами и сортировкой
    await show_tasks_page(callback_query.from_user.id, callback_query.message, page=page, filters=filters, sort_by=sort_by, sort_order=sort_order)
    await callback_query.answer()

def get_filter_description(filters: dict) -> str:
    """Формирует описание примененных фильтров для отображения пользователю"""
    if not filters:
        return ""
    
    # Удаляем поисковый запрос из фильтров для описания
    filters_copy = filters.copy()
    filters_copy.pop('search', None)
    
    if not filters_copy:
        return ""
    
    filter_parts = []
    
    if 'status_id' in filters_copy:
        filter_parts.append(f"Статус: {filters_copy['status_id']}")
    
    if 'priority_id' in filters_copy:
        filter_parts.append(f"Приоритет: {filters_copy['priority_id']}")
    
    if 'type_id' in filters_copy:
        filter_parts.append(f"Тип: {filters_copy['type_id']}")
    
    if 'deadline_from' in filters_copy:
        filter_parts.append(f"Дедлайн от: {filters_copy['deadline_from']}")
    
    if 'deadline_to' in filters_copy:
        filter_parts.append(f"Дедлайн до: {filters_copy['deadline_to']}")
    
    return ", ".join(filter_parts)

@router.message(Command("add_task"))
async def start_add_task(message: Message, dialog_manager: DialogManager):
    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.get_user_by_id(str(message.from_user.id))

        if not user:
            await message.answer("Пользователь не найден. Сначала выполните команду /start")
            return
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
    logger.debug(f"Обработка колбэка settings_statuses от пользователя {user_id}")

    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(str(user_id))

        logger.debug(f"Получено {len(statuses) if statuses else 0} статусов для пользователя {user_id}")

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
    logger.debug(f"Обработка колбэка settings_priorities от пользователя {user_id}")

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
    logger.debug(f"Обработка колбэка settings_durations от пользователя {user_id}")

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
    logger.debug(f"Обработка колбэка settings_task_types от пользователя {user_id}")

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

# Обработчик выбора фильтра по приоритету
@router.callback_query(F.data == "tasks_filter_priority")
async def on_filter_priority_callback(callback_query: CallbackQuery):
    """Обработчик выбора фильтра по приоритету"""
    logger.debug("Получен колбэк для фильтрации по приоритету")
    
    user_id = callback_query.from_user.id
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        priorities = await settings_service.get_priorities(str(user_id))
        
        if not priorities:
            await callback_query.answer("Приоритеты не найдены")
            return
        
        # Создаем клавиатуру с кнопками для выбора приоритета
        keyboard = []
        
        # Группируем кнопки по 2 в ряд
        for i in range(0, len(priorities), 2):
            row = []
            # Добавляем первую кнопку в ряд
            row.append(InlineKeyboardButton(
                text=f"{priorities[i]['name']}",
                callback_data=f"tasks_filter_priority_set_{priorities[i]['id']}"
            ))
            
            # Добавляем вторую кнопку, если она есть
            if i + 1 < len(priorities):
                row.append(InlineKeyboardButton(
                    text=f"{priorities[i + 1]['name']}",
                    callback_data=f"tasks_filter_priority_set_{priorities[i + 1]['id']}"
                ))
            
            keyboard.append(row)
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="tasks_filter"
        )])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с клавиатурой для выбора приоритета
        await callback_query.message.edit_text(
            "Выберите приоритет задачи:",
            reply_markup=markup
        )
        await callback_query.answer()

# Обработчик установки фильтра по приоритету
@router.callback_query(F.data.startswith("tasks_filter_priority_set_"))
async def on_filter_priority_set_callback(callback_query: CallbackQuery):
    """Обработчик установки фильтра по приоритету"""
    logger.debug("Получен колбэк для установки фильтра по приоритету")
    
    # Извлекаем ID приоритета из callback_data
    priority_id = int(callback_query.data.split("_")[-1])
    
    # Извлекаем текущие фильтры из сообщения
    message_text = callback_query.message.text
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Добавляем фильтр по приоритету
    filters["priority_id"] = priority_id
    
    # Показываем первую страницу с примененным фильтром
    await show_tasks_page(callback_query.from_user.id, callback_query.message, page=1, filters=filters, sort_by=sort_by, sort_order=sort_order)
    await callback_query.answer("Фильтр по приоритету применен")

# Обработчик выбора фильтра по типу задачи
@router.callback_query(F.data == "tasks_filter_type")
async def on_filter_type_callback(callback_query: CallbackQuery):
    """Обработчик выбора фильтра по типу задачи"""
    logger.debug("Получен колбэк для фильтрации по типу задачи")
    
    user_id = callback_query.from_user.id
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_types = await settings_service.get_task_types(str(user_id))
        
        if not task_types:
            await callback_query.answer("Типы задач не найдены")
            return
        
        # Создаем клавиатуру с кнопками для выбора типа задачи
        keyboard = []
        
        # Группируем кнопки по 2 в ряд
        for i in range(0, len(task_types), 2):
            row = []
            # Добавляем первую кнопку в ряд
            row.append(InlineKeyboardButton(
                text=f"{task_types[i]['name']}",
                callback_data=f"tasks_filter_type_set_{task_types[i]['id']}"
            ))
            
            # Добавляем вторую кнопку, если она есть
            if i + 1 < len(task_types):
                row.append(InlineKeyboardButton(
                    text=f"{task_types[i + 1]['name']}",
                    callback_data=f"tasks_filter_type_set_{task_types[i + 1]['id']}"
                ))
            
            keyboard.append(row)
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="tasks_filter"
        )])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с клавиатурой для выбора типа задачи
        await callback_query.message.edit_text(
            "Выберите тип задачи:",
            reply_markup=markup
        )
        await callback_query.answer()

# Обработчик установки фильтра по типу задачи
@router.callback_query(F.data.startswith("tasks_filter_type_set_"))
async def on_filter_type_set_callback(callback_query: CallbackQuery):
    """Обработчик установки фильтра по типу задачи"""
    logger.debug("Получен колбэк для установки фильтра по типу задачи")
    
    # Извлекаем ID типа задачи из callback_data
    type_id = int(callback_query.data.split("_")[-1])
    
    # Извлекаем текущие фильтры из сообщения
    message_text = callback_query.message.text
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Добавляем фильтр по типу задачи
    filters["type_id"] = type_id
    
    # Показываем первую страницу с примененным фильтром
    await show_tasks_page(callback_query.from_user.id, callback_query.message, page=1, filters=filters, sort_by=sort_by, sort_order=sort_order)
    await callback_query.answer("Фильтр по типу задачи применен")

# Обработчик выбора фильтра по дедлайну
@router.callback_query(F.data == "tasks_filter_deadline")
async def on_filter_deadline_callback(callback_query: CallbackQuery):
    """Обработчик выбора фильтра по дедлайну"""
    logger.debug("Получен колбэк для фильтрации по дедлайну")
    
    # Создаем клавиатуру с кнопками для выбора периода дедлайна
    keyboard = [
        [
            InlineKeyboardButton(
                text="Сегодня",
                callback_data="deadline_set_today"
            ),
            InlineKeyboardButton(
                text="Завтра",
                callback_data="deadline_set_tomorrow"
            )
        ],
        [
            InlineKeyboardButton(
                text="Эта неделя",
                callback_data="deadline_set_thisweek"
            ),
            InlineKeyboardButton(
                text="Следующая неделя",
                callback_data="deadline_set_nextweek"
            )
        ],
        [
            InlineKeyboardButton(
                text="Этот месяц",
                callback_data="deadline_set_thismonth"
            ),
            InlineKeyboardButton(
                text="Следующий месяц",
                callback_data="deadline_set_nextmonth"
            )
        ],
        [
            InlineKeyboardButton(
                text="Просроченные",
                callback_data="deadline_set_overdue"
            )
        ],
        [
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="tasks_filter"
            )
        ]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем сообщение с клавиатурой для выбора периода дедлайна
    await callback_query.message.edit_text(
        "Выберите период дедлайна:",
        reply_markup=markup
    )
    await callback_query.answer()

# Обработчик установки фильтра по дедлайну
@router.callback_query(F.data.startswith("deadline_set_"))
async def on_filter_deadline_set_callback(callback_query: CallbackQuery):
    """Обработчик установки фильтра по дедлайну"""
    logger.debug("Получен колбэк для установки фильтра по дедлайну")
    
    # Извлекаем период дедлайна из callback_data
    period = callback_query.data.split("_")[-1]
    logger.debug(f"Выбран период дедлайна: {period}")
    
    # Получаем даты для фильтрации
    today = datetime.now().date()
    
    # Определяем даты начала и конца периода
    date_from = None
    date_to = None
    
    try:
        if period == "today":
            date_from = today
            date_to = today
        elif period == "tomorrow":
            date_from = today + timedelta(days=1)
            date_to = date_from
        elif period == "thisweek":
            # Начало недели - понедельник
            date_from = today - timedelta(days=today.weekday())
            # Конец недели - воскресенье
            date_to = date_from + timedelta(days=6)
        elif period == "nextweek":
            # Начало следующей недели
            date_from = today + timedelta(days=(7 - today.weekday()))
            # Конец следующей недели
            date_to = date_from + timedelta(days=6)
        elif period == "thismonth":
            # Начало текущего месяца
            date_from = today.replace(day=1)
            # Конец текущего месяца
            if today.month == 12:
                date_to = today.replace(day=31)
            else:
                date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        elif period == "nextmonth":
            # Начало следующего месяца
            if today.month == 12:
                date_from = today.replace(year=today.year + 1, month=1, day=1)
            else:
                date_from = today.replace(month=today.month + 1, day=1)
            # Конец следующего месяца
            if date_from.month == 12:
                date_to = date_from.replace(day=31)
            else:
                date_to = date_from.replace(month=date_from.month + 1, day=1) - timedelta(days=1)
        elif period == "overdue":
            date_to = today - timedelta(days=1)
            date_from = None  # Для просроченных задач не устанавливаем нижнюю границу
        else:
            logger.error(f"Неверный период дедлайна: {period}")
            await callback_query.answer("Неверный период")
            return
            
        logger.debug(f"Рассчитанные даты: с {date_from} по {date_to}")
    except Exception as e:
        logger.error(f"Ошибка при расчете дат для периода {period}: {e}")
        await callback_query.answer("Ошибка при установке фильтра")
        return
    
    # Создаем минимальный набор фильтров для дедлайна
    filters = {}
    
    # Добавляем фильтр по дедлайну
    if date_from:
        filters["deadline_from"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        filters["deadline_to"] = date_to.strftime("%Y-%m-%d")
    
    try:
        # Показываем первую страницу с примененным фильтром
        await show_tasks_page(callback_query.from_user.id, callback_query.message, page=1, filters=filters)
        await callback_query.answer("Фильтр по дедлайну применен")
    except Exception as e:
        logger.error(f"Ошибка при применении фильтра по дедлайну: {e}")
        await callback_query.answer("Ошибка при применении фильтра")
        # Возвращаемся к экрану фильтров
        await on_filter_button_callback(callback_query)

# Обработчик нажатия на кнопку поиска
@router.callback_query(F.data.startswith("tasks_search_"))
async def on_search_button_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку поиска"""
    logger.debug("Получен колбэк для поиска задач")
    
    # Извлекаем фильтры и параметры сортировки из callback_data
    parts = callback_query.data.split("_", 3)
    
    # Сохраняем текущие фильтры и параметры сортировки в состоянии
    filters = {}
    sort_by = None
    sort_order = "asc"
    
    if len(parts) > 3:
        # Формат: tasks_search_encoded_filters_sort_by_sort_order
        remaining_parts = parts[3].split("_")
        
        if len(remaining_parts) >= 1 and remaining_parts[0]:
            filters = decode_filters(remaining_parts[0])
        
        if len(remaining_parts) >= 2 and remaining_parts[1]:
            sort_by = remaining_parts[1]
        
        if len(remaining_parts) >= 3 and remaining_parts[2]:
            sort_order = remaining_parts[2]
    
    # Сохраняем данные в состоянии
    await state.set_state(SearchStates.waiting_for_query)
    await state.update_data(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        message_id=callback_query.message.message_id
    )
    
    # Отправляем сообщение с запросом поискового запроса
    await callback_query.message.answer(
        "Введите текст для поиска задач (или отправьте /cancel для отмены):"
    )
    await callback_query.answer()

# Обработчик ввода поискового запроса
@router.message(SearchStates.waiting_for_query)
async def on_search_query_input(message: Message, state: FSMContext):
    """Обработчик ввода поискового запроса"""
    # Получаем данные из состояния
    data = await state.get_data()
    filters = data.get('filters', {})
    sort_by = data.get('sort_by')
    sort_order = data.get('sort_order', 'asc')
    
    # Получаем поисковый запрос
    search_query = message.text.strip()
    
    # Проверяем, не отменил ли пользователь поиск
    if search_query.lower() == '/cancel':
        await state.clear()
        await message.answer("Поиск отменен")
        return
    
    # Добавляем поисковый запрос в фильтры
    filters['search'] = search_query
    
    # Очищаем состояние
    await state.clear()
    
    # Показываем результаты поиска
    await show_tasks_page(message.from_user.id, message, page=1, filters=filters, sort_by=sort_by, sort_order=sort_order)
    
    # Отправляем сообщение об успешном поиске
    await message.answer(f"Поиск по запросу: '{search_query}'")

# Обработчик нажатия на кнопку "Сбросить фильтры"
@router.callback_query(F.data == "tasks_reset_filters")
async def on_reset_filters_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку сброса фильтров"""
    logger.debug("Получен колбэк для сброса фильтров")
    
    # Извлекаем информацию о сортировке из текста сообщения
    message_text = callback_query.message.text
    sort_by = None
    sort_order = "asc"
    
    # Проверяем, есть ли информация о сортировке в сообщении
    if "Сортировка:" in message_text:
        sort_line = next((line for line in message_text.split('\n') if "Сортировка:" in line), None)
        if sort_line:
            # Извлекаем поле сортировки
            for field, name in {
                "title": "по названию",
                "deadline": "по дедлайну",
                "priority": "по приоритету",
                "status": "по статусу",
                "created_at": "по дате создания",
                "completed_at": "по дате завершения"
            }.items():
                if name in sort_line:
                    sort_by = field
                    break
            
            # Определяем порядок сортировки
            sort_order = "desc" if "по убыванию" in sort_line else "asc"
    
    # Показываем первую страницу без фильтров, но с сохранением сортировки, если она была
    await show_tasks_page(
        callback_query.from_user.id, 
        callback_query.message, 
        page=1, 
        filters={}, 
        sort_by=sort_by, 
        sort_order=sort_order
    )
    
    await callback_query.answer("Фильтры сброшены")

# Обработчик нажатия на кнопку "Сбросить сортировку"
@router.callback_query(F.data == "tasks_reset_sort")
async def on_reset_sort_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопку сброса сортировки"""
    logger.debug("Получен колбэк для сброса сортировки")
    
    # Извлекаем информацию о фильтрах из текста сообщения
    message_text = callback_query.message.text
    filters = {}
    
    # Проверяем, есть ли информация о фильтрах в сообщении
    if "Фильтры:" in message_text:
        filter_line = next((line for line in message_text.split('\n') if "Фильтры:" in line), None)
        if filter_line:
            filter_text = filter_line.replace("Фильтры:", "").strip()
            filter_parts = filter_text.split(", ")
            
            for part in filter_parts:
                if ":" in part:
                    key, value = part.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == "статус":
                        filters["status_id"] = value
                    elif key == "приоритет":
                        filters["priority_id"] = value
                    elif key == "тип":
                        filters["type_id"] = value
                    elif key == "дедлайн от":
                        filters["deadline_from"] = value
                    elif key == "дедлайн до":
                        filters["deadline_to"] = value
    
    # Проверяем, есть ли информация о поиске в сообщении
    if "Поиск:" in message_text:
        search_line = next((line for line in message_text.split('\n') if "Поиск:" in line), None)
        if search_line:
            search_query = search_line.replace("Поиск:", "").strip()
            # Удаляем кавычки вокруг запроса
            search_query = search_query.strip("'")
            if search_query:
                filters["search"] = search_query
    
    # Показываем первую страницу с текущими фильтрами, но без сортировки
    await show_tasks_page(
        callback_query.from_user.id, 
        callback_query.message, 
        page=1, 
        filters=filters
    )
    
    await callback_query.answer("Сортировка сброшена")
