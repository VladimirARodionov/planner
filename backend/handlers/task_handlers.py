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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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

@router.message(Command("tasks"))
async def list_tasks(message: Message):
    """Показать список задач с пагинацией"""
    await show_tasks_page(message, page=1)

async def show_tasks_page(message: Message, page: int = 1, callback_query: CallbackQuery = None, filters: dict = None, sort_by: str = None, sort_order: str = "asc"):
    """Показать страницу списка задач с пагинацией"""
    # Количество задач на одной странице
    page_size = 3
    
    # Вычисляем смещение для запроса
    offset = (page - 1) * page_size
    
    user_id = message.from_user.id if message else callback_query.from_user.id
    logger.debug(f"Показываем страницу {page} списка задач для пользователя {user_id}")
    
    # Инициализируем фильтры, если они не переданы
    if filters is None:
        filters = {}
    
    async with get_session() as session:
        task_service = TaskService(session)
        # Получаем общее количество задач для пользователя с учетом фильтров
        all_tasks = await task_service.get_tasks(str(user_id), filters)
        
        # Применяем сортировку, если указана
        if sort_by:
            logger.debug(f"Сортировка задач по {sort_by} в порядке {sort_order}")
            reverse = sort_order == "desc"
            
            if sort_by == "title":
                all_tasks.sort(key=lambda x: x['title'].lower(), reverse=reverse)
            elif sort_by == "deadline":
                # Сортируем по дедлайну, задачи без дедлайна в конце
                all_tasks.sort(
                    key=lambda x: (x['deadline'] is None, x['deadline']), 
                    reverse=reverse
                )
            elif sort_by == "priority":
                # Сортируем по приоритету, задачи без приоритета в конце
                all_tasks.sort(
                    key=lambda x: (
                        x['priority'] is None, 
                        -x['priority']['order'] if x['priority'] else 0
                    ), 
                    reverse=reverse
                )
            elif sort_by == "status":
                # Сортируем по статусу, задачи без статуса в конце
                all_tasks.sort(
                    key=lambda x: (
                        x['status'] is None, 
                        x['status']['order'] if x['status'] else 0
                    ), 
                    reverse=reverse
                )
        
        total_tasks = len(all_tasks)
        
        # Получаем задачи для текущей страницы
        tasks = all_tasks[offset:offset + page_size] if offset < total_tasks else []
        
        logger.debug(f"Получено {len(tasks)} задач для страницы {page} (всего {total_tasks} задач)")

        # Если задач нет, показываем сообщение
        if not tasks and page == 1:
            if callback_query:
                await callback_query.message.edit_text(i18n.format_value("tasks-empty"))
            else:
                await message.answer(i18n.format_value("tasks-empty"))
            return

        # Если запрошена страница, которой нет, показываем первую страницу
        if not tasks and page > 1:
            logger.debug(f"Запрошена несуществующая страница {page}, показываем первую страницу")
            await show_tasks_page(message, page=1, callback_query=callback_query, filters=filters, sort_by=sort_by, sort_order=sort_order)
            return

        # Формируем текст сообщения
        total_pages = (total_tasks + page_size - 1) // page_size
        
        # Добавляем информацию о примененных фильтрах и сортировке
        filter_info = ""
        if filters:
            filter_parts = []
            
            # Получаем информацию о настройках пользователя для отображения названий фильтров
            settings_service = SettingsService(session)
            settings = await settings_service.get_settings(str(user_id))
            
            if filters.get('status_id'):
                status_name = next((s['name'] for s in settings['statuses'] if s['id'] == filters['status_id']), "Неизвестный")
                filter_parts.append(f"Статус: {status_name}")
            
            if filters.get('priority_id'):
                priority_name = next((p['name'] for p in settings['priorities'] if p['id'] == filters['priority_id']), "Неизвестный")
                filter_parts.append(f"Приоритет: {priority_name}")
            
            if filters.get('type_id'):
                type_name = next((t['name'] for t in settings['task_types'] if t['id'] == filters['type_id']), "Неизвестный")
                filter_parts.append(f"Тип: {type_name}")
            
            if filter_parts:
                filter_info = " [" + ", ".join(filter_parts) + "]"
        
        # Добавляем информацию о сортировке
        sort_info = ""
        if sort_by:
            sort_name = {
                "title": "названию",
                "deadline": "дедлайну",
                "priority": "приоритету",
                "status": "статусу"
            }.get(sort_by, sort_by)
            
            sort_direction = "↓" if sort_order == "desc" else "↑"
            sort_info = f" (Сортировка: {sort_name} {sort_direction})"
        
        response = i18n.format_value("tasks-header") + filter_info + sort_info + f" (Страница {page}/{total_pages})\n\n"
        
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

            if task['duration']:
                response += i18n.format_value("task-duration-line", {
                    "duration": f"{task['duration']['name']} ({task['duration']['value']} {task['duration']['type']})"
                }) + "\n"
                
            if task['deadline']:
                response += i18n.format_value("task-deadline-line", {
                    "deadline": task['deadline']
                }) + "\n"
                
            response += "\n"
        
        # Создаем клавиатуру для навигации
        keyboard = []
        navigation_row = []
        
        # Кнопка "Предыдущая страница"
        if page > 1:
            navigation_row.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"tasks_page_{page-1}_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
            ))
        
        # Кнопка "Следующая страница"
        if page < total_pages:
            navigation_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=f"tasks_page_{page+1}_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
            ))
        
        # Добавляем кнопки навигации, если они есть
        if navigation_row:
            keyboard.append(navigation_row)
        
        # Добавляем кнопки фильтрации
        filter_row = []
        
        # Кнопка фильтрации по статусу
        filter_row.append(InlineKeyboardButton(
            text="🔍 Статус",
            callback_data=f"tasks_filter_status_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
        ))
        
        # Кнопка фильтрации по приоритету
        filter_row.append(InlineKeyboardButton(
            text="🔍 Приоритет",
            callback_data=f"tasks_filter_priority_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
        ))
        
        # Кнопка фильтрации по типу
        filter_row.append(InlineKeyboardButton(
            text="🔍 Тип",
            callback_data=f"tasks_filter_type_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
        ))
        
        keyboard.append(filter_row)
        
        # Добавляем кнопки сортировки
        sort_row = []
        
        # Кнопка сортировки по названию
        sort_icon = ""
        if sort_by == "title":
            sort_icon = "↓" if sort_order == "desc" else "↑"
        sort_row.append(InlineKeyboardButton(
            text=f"📝 Название {sort_icon}",
            callback_data=f"tasks_sort_title_{encode_filters(filters)}"
        ))
        
        # Кнопка сортировки по дедлайну
        sort_icon = ""
        if sort_by == "deadline":
            sort_icon = "↓" if sort_order == "desc" else "↑"
        sort_row.append(InlineKeyboardButton(
            text=f"⏰ Дедлайн {sort_icon}",
            callback_data=f"tasks_sort_deadline_{encode_filters(filters)}"
        ))
        
        keyboard.append(sort_row)
        
        # Вторая строка сортировки
        sort_row2 = []
        
        # Кнопка сортировки по приоритету
        sort_icon = ""
        if sort_by == "priority":
            sort_icon = "↓" if sort_order == "desc" else "↑"
        sort_row2.append(InlineKeyboardButton(
            text=f"🔥 Приоритет {sort_icon}",
            callback_data=f"tasks_sort_priority_{encode_filters(filters)}"
        ))
        
        # Кнопка сортировки по статусу
        sort_icon = ""
        if sort_by == "status":
            sort_icon = "↓" if sort_order == "desc" else "↑"
        sort_row2.append(InlineKeyboardButton(
            text=f"🔄 Статус {sort_icon}",
            callback_data=f"tasks_sort_status_{encode_filters(filters)}"
        ))
        
        keyboard.append(sort_row2)
        
        # Добавляем кнопку сброса фильтров, если они применены
        if filters:
            keyboard.append([InlineKeyboardButton(
                text="❌ Сбросить фильтры",
                callback_data=f"tasks_filter_reset_{sort_by or ''}_{sort_order}"
            )])
        
        # Добавляем кнопку сброса сортировки, если она применена
        if sort_by:
            keyboard.append([InlineKeyboardButton(
                text="❌ Сбросить сортировку",
                callback_data=f"tasks_sort_reset_{encode_filters(filters)}"
            )])
        
        # Добавляем кнопку обновления
        keyboard.append([InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=f"tasks_page_{page}_{encode_filters(filters)}_{sort_by or ''}_{sort_order}"
        )])
        
        # Создаем разметку клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем или редактируем сообщение
        if callback_query:
            await callback_query.message.edit_text(response, reply_markup=markup)
            await callback_query.answer()
        else:
            await message.answer(response, reply_markup=markup)

# Функции для кодирования и декодирования фильтров
def encode_filters(filters: dict) -> str:
    """Кодирует фильтры в строку для использования в callback_data"""
    if not filters:
        return ""
    
    # Преобразуем словарь в JSON-строку
    json_str = json.dumps(filters)
    
    # Кодируем в base64 для безопасной передачи в callback_data
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
        filters = json.loads(json_str)
        
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
    
    # Показываем запрошенную страницу с фильтрами и сортировкой
    await show_tasks_page(None, page=page, callback_query=callback_query, filters=filters, sort_by=sort_by, sort_order=sort_order)

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
    await show_tasks_page(None, page=1, callback_query=callback_query, filters={}, sort_by=sort_by, sort_order=sort_order)

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
    await show_tasks_page(None, page=1, callback_query=callback_query, filters=filters)

# Обработчик нажатия на кнопки сортировки
@router.callback_query(F.data.startswith("tasks_sort_"))
async def on_tasks_sort_callback(callback_query: CallbackQuery):
    """Обработчик нажатия на кнопки сортировки"""
    # Извлекаем параметр сортировки и фильтры из callback_data
    parts = callback_query.data.split("_", 3)
    
    # Пропускаем обработку для кнопки сброса сортировки
    if parts[2] == "reset":
        return
    
    sort_by = parts[2]
    
    # Проверяем, есть ли фильтры
    filters = {}
    
    if len(parts) > 3:
        # Формат: tasks_sort_sort_by_encoded_filters
        filters = decode_filters(parts[3])
    
    # Определяем порядок сортировки
    # Если уже сортируем по этому полю, меняем порядок сортировки
    current_sort_by = None
    current_sort_order = "asc"
    
    # Проверяем текущую сортировку из callback_query.message
    if callback_query.message and callback_query.message.reply_markup:
        for row in callback_query.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data and button.callback_data.startswith("tasks_page_"):
                    # Формат: tasks_page_1_encoded_filters_sort_by_sort_order
                    button_parts = button.callback_data.split("_", 3)
                    if len(button_parts) > 3:
                        remaining_parts = button_parts[3].split("_")
                        if len(remaining_parts) >= 2 and remaining_parts[1]:
                            current_sort_by = remaining_parts[1]
                        if len(remaining_parts) >= 3 and remaining_parts[2]:
                            current_sort_order = remaining_parts[2]
                    break
    
    # Если уже сортируем по этому полю, меняем порядок сортировки
    sort_order = "desc" if (current_sort_by == sort_by and current_sort_order == "asc") else "asc"
    
    logger.debug(f"Получен колбэк для сортировки по {sort_by} в порядке {sort_order}, фильтры: {filters}")
    
    # Показываем первую страницу с фильтрами и сортировкой
    await show_tasks_page(None, page=1, callback_query=callback_query, filters=filters, sort_by=sort_by, sort_order=sort_order)

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

@router.message(Command("create_settings"))
async def create_settings_command(message: Message):
    """Принудительно создает настройки для пользователя"""
    user_id = message.from_user.id
    logger.debug(f"Команда /create_settings от пользователя {user_id}")
    
    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.get_user_by_id(str(user_id))
        
        if not user:
            await message.answer("Пользователь не найден. Сначала выполните команду /start")
            return
        
        try:
            # Принудительно создаем настройки для пользователя
            await create_user_settings(user.telegram_id, session)
            logger.debug(f"Настройки для пользователя {user_id} созданы успешно")
            await message.answer("Настройки успешно созданы!")
        except Exception as e:
            logger.error(f"Ошибка при создании настроек для пользователя {user_id}: {e}")
            await message.answer(f"Ошибка при создании настроек: {e}")

@router.message(Command("settings_statuses"))
async def show_statuses_settings(message: Message):
    """Показать настройки статусов задач"""
    user_id = message.from_user.id
    logger.debug(f"Запрос настроек статусов для пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(str(user_id))
        
        logger.debug(f"Получено {len(statuses) if statuses else 0} статусов для пользователя {user_id}")
        
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
    logger.debug(f"Запрос настроек длительностей для пользователя {user_id}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        durations = await settings_service.get_durations(str(user_id))
        
        logger.debug(f"Получено {len(durations) if durations else 0} длительностей для пользователя {user_id}")
        
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

# Обработчик команды поиска задач
@router.message(Command("search"))
async def search_tasks(message: Message):
    """Обработчик команды поиска задач"""
    # Получаем текст запроса из сообщения
    query_text = message.text.replace("/search", "").strip()
    
    if not query_text:
        # Если запрос пустой, просим пользователя ввести поисковый запрос
        await message.answer("Пожалуйста, введите поисковый запрос после команды /search")
        return
    
    logger.debug(f"Поиск задач по запросу: {query_text}")
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        task_service = TaskService(session)
        # Получаем все задачи пользователя
        all_tasks = await task_service.get_tasks(str(user_id), {})
        
        # Фильтруем задачи по поисковому запросу
        found_tasks = []
        for task in all_tasks:
            # Проверяем, содержится ли запрос в названии или описании задачи
            title = task['title'].lower()
            description = task['description'].lower() if task['description'] else ""
            
            if query_text.lower() in title or query_text.lower() in description:
                found_tasks.append(task)
        
        # Если задачи не найдены, сообщаем об этом
        if not found_tasks:
            await message.answer(f"По запросу '{query_text}' ничего не найдено")
            return
        
        # Формируем текст сообщения с результатами поиска
        response = f"Результаты поиска по запросу '{query_text}' ({len(found_tasks)} найдено):\n\n"
        
        for task in found_tasks:
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
        
        # Создаем клавиатуру с кнопкой для просмотра всех задач
        keyboard = [[InlineKeyboardButton(
            text="Показать все задачи",
            callback_data="tasks_page_1__"
        )]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с результатами поиска
        await message.answer(response, reply_markup=markup)

# Обработчик команды поиска задач с диалогом
@router.message(Command("find"))
async def start_search_dialog(message: Message, state: FSMContext):
    """Обработчик команды поиска задач с диалогом"""
    # Отправляем сообщение с просьбой ввести поисковый запрос
    await message.answer("Введите текст для поиска задач:")
    
    # Устанавливаем состояние ожидания ввода поискового запроса
    await state.set_state(SearchStates.waiting_for_query)

# Обработчик ввода поискового запроса
@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    """Обработчик ввода поискового запроса"""
    # Получаем текст запроса из сообщения
    query_text = message.text.strip()
    
    # Сбрасываем состояние
    await state.clear()
    
    logger.debug(f"Поиск задач по запросу: {query_text}")
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        task_service = TaskService(session)
        # Получаем все задачи пользователя
        all_tasks = await task_service.get_tasks(str(user_id), {})
        
        # Фильтруем задачи по поисковому запросу
        found_tasks = []
        for task in all_tasks:
            # Проверяем, содержится ли запрос в названии или описании задачи
            title = task['title'].lower()
            description = task['description'].lower() if task['description'] else ""
            
            if query_text.lower() in title or query_text.lower() in description:
                found_tasks.append(task)
        
        # Если задачи не найдены, сообщаем об этом
        if not found_tasks:
            await message.answer(f"По запросу '{query_text}' ничего не найдено")
            return
        
        # Формируем текст сообщения с результатами поиска
        response = f"Результаты поиска по запросу '{query_text}' ({len(found_tasks)} найдено):\n\n"
        
        for task in found_tasks:
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
        
        # Создаем клавиатуру с кнопкой для просмотра всех задач
        keyboard = [[InlineKeyboardButton(
            text="Показать все задачи",
            callback_data="tasks_page_1__"
        )]]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отправляем сообщение с результатами поиска
        await message.answer(response, reply_markup=markup) 