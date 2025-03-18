import logging
import time
import json
import os
import jwt
import uuid
from datetime import datetime, timedelta, UTC
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from backend.database import get_session, create_user_settings
from backend.dialogs.task_list_dialog import TaskListStates
from backend.locale_config import i18n, get_user_locale, AVAILABLE_LANGUAGES, set_user_locale, set_current_user_id
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(user_id))
    
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

            # Отправляем сообщение с кнопкой для входа
            await message.answer(
                i18n.format_value("web-auth-success"),
                reply_markup=keyboard
            )

            if "https://" in auth_url:
                # Создаем клавиатуру с кнопкой для входа через Mini App
                mini_app_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=i18n.format_value("login-to-web-mini-app"),
                        web_app={"url": auth_url}
                    )]
                ])
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(message.from_user.id))
    await message.answer(i18n.format_value("stopped"))

# Функция для отображения справки
async def show_help(message: Message):
    """Показать справку по командам"""
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(message.from_user.id))
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
            "\n" +
            i18n.format_value("settings_language_help") + "\n" +
            "\n" +
            i18n.format_value("help-help")
    )
    await message.answer(help_text)

@router.message(Command("help"))
async def help_command(message: Message):
    """Показать справку по командам"""
    await show_help(message)

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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(message.from_user.id))
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(user_id))
    
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(user_id))
    
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(user_id))
    
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
    # Устанавливаем пользователя в контекст
    set_current_user_id(str(user_id))
    
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

@router.message(Command("tasks"))
async def list_tasks(message: Message, dialog_manager: DialogManager):
    """Показать список задач с пагинацией"""
    try:
        # Запускаем диалог списка задач с начальными данными
        await dialog_manager.start(TaskListStates.main, data={"page": 1, "filters": {}})
    except Exception as e:
        logger.exception(f"Ошибка при запуске диалога списка задач: {e}")
        await message.answer(f"Произошла ошибка при загрузке списка задач: {e}")

@router.message(Command("language"))
async def language_command(message: Message):
    """Обработчик команды выбора языка"""
    user_id = str(message.from_user.id)
    
    # Устанавливаем пользователя в контекст
    set_current_user_id(user_id)
    
    # Получаем локализацию пользователя
    user_locale = await get_user_locale(user_id)
    
    # Создаем клавиатуру с кнопками выбора языка
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🇷🇺 Русский",
            callback_data="language_ru"
        )],
        [InlineKeyboardButton(
            text="🇬🇧 English",
            callback_data="language_en"
        )]
    ])

    await message.answer(
        user_locale.format_value("language_selection_header"),
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("language_"))
async def language_callback(callback_query: CallbackQuery):
    """Обработчик выбора языка"""
    await callback_query.answer()
    
    user_id = str(callback_query.from_user.id)
    
    # Устанавливаем пользователя в контекст
    set_current_user_id(user_id)
    
    language = callback_query.data.split("_")[1]
    
    if language not in AVAILABLE_LANGUAGES:
        await callback_query.message.answer(i18n.format_value("language_not_supported"))
        return
    
    # Обновляем язык пользователя в кеше
    success = set_user_locale(user_id, language)
    
    if success:
        # Сохраняем выбранный язык в базе данных
        async with get_session() as session:
            auth_service = AuthService(session)
            await auth_service.set_user_language(user_id, language)
            
            # Устанавливаем флаг для обновления команд бота
            await auth_service.set_user_bot_update_flag(user_id, True)
            logger.debug(f"Установлен флаг обновления бота для пользователя {user_id}")
        
        # Дополнительно загружаем обновленные локализации в кеш
        from backend.locale_config import reload_user_locale
        reload_success = await reload_user_locale(user_id)
        logger.debug(f"Локализация перезагружена: {reload_success}")

        # Получаем обновленную локализацию
        user_locale = await get_user_locale(user_id)
        
        await callback_query.message.answer(user_locale.format_value("language_changed"))
        
        # Немедленно обновляем команды бота вместо ожидания фоновой задачи
        from backend.run import main_bot, set_user_commands
        try:
            await set_user_commands(main_bot, user_id, user_locale)
            logger.info(f"Немедленно обновлены команды бота для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при немедленном обновлении команд бота: {e}")
    else:
        # Получаем обновленную локализацию с await
        user_locale = await get_user_locale(user_id)
        await callback_query.message.answer(user_locale.format_value("language_change_error"))
