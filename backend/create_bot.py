import os
import pathlib

import decouple
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import create_engine

# настраиваем логирование и выводим в переменную для отдельного использования в нужных местах
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
    db_host = 'plannerdb'
    db_port = env_config.get('POSTGRES_PORT') or '5432'
    db_string = 'postgresql://{}:{}@{}:{}/{}'.format(db_user, db_pass, db_host, db_port, db_name)
else:
    db_string = 'sqlite:///local.db'
db = create_engine(
    db_string,
    **(
        dict(pool_recycle=900, pool_size=100, max_overflow=3)
    )
)

# инициируем объект бота, передавая ему parse_mode=ParseMode.HTML по умолчанию
main_bot = Bot(token=env_config.get('TELEGRAM_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# инициируем объект бота
dp = Dispatcher()
