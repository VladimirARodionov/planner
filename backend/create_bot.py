import os
import pathlib
import logging

import decouple
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from fluent.runtime import FluentLocalization
from sqlalchemy import create_engine

# настраиваем логирование
logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", default="DEVELOPMENT")

def get_env_config() -> decouple.Config:
    """
    Creates and returns a Config object based on the environment setting.
    It uses .env.dev for development and .env for production.
    """
    env_files = {
        "DEVELOPMENT": ".env.dev",
        "PRODUCTION": ".env",
    }

    app_dir_path = pathlib.Path(__file__).resolve().parent.parent
    env_file_name = env_files.get(ENVIRONMENT, ".env.dev")
    file_path = app_dir_path / env_file_name

    if not file_path.is_file():
        raise FileNotFoundError(f"Environment file not found: {file_path}")

    return decouple.Config(decouple.RepositoryEnv(file_path))


env_config = get_env_config()
# получаем список администраторов из .env
superusers = [int(superuser_id) for superuser_id in env_config.get('SUPERUSERS').split(',')]
LOGGER_LEVEL = env_config.get('LOGGER_LEVEL')

# Connect to the database
if ENVIRONMENT == 'PRODUCTION':
    db_name = env_config.get('POSTGRES_DB')
    db_user = env_config.get('POSTGRES_USER')
    db_pass = env_config.get('POSTGRES_PASSWORD')
    db_host = 'postgres'
    db_port = env_config.get('POSTGRES_PORT') or '5432'
    db_string = 'postgresql+asyncpg://{}:{}@{}:{}/{}'.format(db_user, db_pass, db_host, db_port, db_name)
    db_string_sync = 'postgresql://{}:{}@{}:{}/{}'.format(db_user, db_pass, db_host, db_port, db_name)
else:
    db_string = 'sqlite+aiosqlite:///local.db'
    db_string_sync = 'sqlite:///local.db'

db = create_engine(
    db_string_sync,
    **(
        dict(pool_recycle=100, pool_size=10, max_overflow=3)
    )
)
# инициируем объект бота, передавая ему parse_mode=ParseMode.HTML по умолчанию
main_bot = Bot(token=env_config.get('TELEGRAM_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Создаем хранилище состояний
storage = MemoryStorage()

# инициируем объект бота
dp = Dispatcher(storage=storage)

def get_bot_commands(user_locale: FluentLocalization = None):
    if not user_locale:
        from backend.locale_config import i18n
        user_locale = i18n

    commands = [
        BotCommand(command='start', description=user_locale.format_value("start_menu")),
        #BotCommand(command='profile', description=user_locale.format_value("my_profile_menu")),
        BotCommand(command='tasks', description=user_locale.format_value("tasks-menu")),
        BotCommand(command='add_task', description=user_locale.format_value("add-task-menu")),
        BotCommand(command='settings', description=user_locale.format_value("settings_menu")),
        BotCommand(command='language', description=user_locale.format_value("settings_language")),
        BotCommand(command='help', description=user_locale.format_value("help-menu")),
        BotCommand(command='stop', description=user_locale.format_value("stop_menu"))
    ]
    return commands
