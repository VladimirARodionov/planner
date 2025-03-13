import asyncio
import logging.config
import pathlib
from asyncio import set_event_loop, new_event_loop
from multiprocessing import Process

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram_dialog import setup_dialogs
from flask import Flask
from flask_jwt_extended import JWTManager

from flask_cors import CORS

from backend.cache_config import cache
from backend.create_bot import main_bot, dp
from backend.dialogs.task_dialogs import task_dialog
from backend.handlers import task_handlers
from backend.load_env import env_config
from backend.locale_config import i18n

logging.config.fileConfig(fname=pathlib.Path(__file__).resolve().parent.parent / 'logging.ini',
                          disable_existing_loggers=False)
logging.getLogger('aiosqlite').propagate = False

logger = logging.getLogger(__name__)

def start_process_aiogram():
    process = Process(target=on_startup, daemon=True)
    process.start()
    return process

def on_startup():
    logger.info('Бот стартован.')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Клавиатурное прерывание')
    except asyncio.CancelledError:
        logger.info('Прерывание')

# Функция, которая выполнится когда бот запустится
async def start_bot(bot: Bot):
    await set_commands(bot)
    logger.info('Бот стартован')


# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands(bot: Bot):
    commands = [BotCommand(command='start', description=i18n.format_value("start_menu")),
                BotCommand(command='profile', description=i18n.format_value("my_profile_menu")),
                BotCommand(command='tasks', description=i18n.format_value("tasks-menu")),
                BotCommand(command='add_task', description=i18n.format_value("add-task-menu")),
                BotCommand(command='settings', description=i18n.format_value("settings_menu")),
                BotCommand(command='help', description=i18n.format_value("help-menu")),
                BotCommand(command='stop', description=i18n.format_value("stop_menu"))]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot(bot: Bot):
    logger.info('Бот остановлен')

async def main():
    # Инициализируем базу данных
    from backend.database import init_db
    await init_db()
    
    # Регистрируем роутеры
    dp.include_router(task_handlers.router)
    dp.include_router(task_dialog)
    # Регистрируем диалоги
    setup_dialogs(dp)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    logger.info('Бот запущен.')
    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await main_bot.delete_webhook(drop_pending_updates=True)
        set_event_loop(new_event_loop())
        await dp.start_polling(main_bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        pass
    finally:
        await main_bot.session.close()
        logger.info('Бот остановлен.')

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})
    
    # Настройка CORS
    #CORS(app, resources={r"/*": {"origins": "*"}})
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "expose_headers": ["Content-Range", "X-Content-Range"]
             }
         },
         allow_headers=["Content-Type", "Authorization"],
         expose_headers=["Content-Range", "X-Content-Range"],
         supports_credentials=True
    )
    
    app.config.from_mapping(
        SECRET_KEY=env_config.get('SECRET_KEY'),
        JWT_SECRET_KEY=env_config.get('JWT_SECRET_KEY'),
        JWT_ACCESS_TOKEN_EXPIRES=3600,  # 1 hour
        JWT_REFRESH_TOKEN_EXPIRES=2592000,  # 30 days
        JWT_TOKEN_LOCATION=["headers"],
        JWT_HEADER_NAME="Authorization",
        JWT_HEADER_TYPE="Bearer"
    )
    # apply the blueprints to the app
    from backend.blueprints import auth_bp, planner_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(planner_bp)

    jwt = JWTManager(app)
    app.debug = True
    return app, jwt


def run_flask(app):
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

if __name__ == '__main__':
    # Создаем приложение Flask
    app, jwt = create_app()
    
    # Запускаем бота в отдельном процессе
    bot_process = start_process_aiogram()
    
    try:
        # Запускаем Flask в основном процессе
        run_flask(app)
    except KeyboardInterrupt:
        logger.info('Завершение работы приложения')
    finally:
        # Завершаем процесс бота при выходе
        if bot_process.is_alive():
            bot_process.terminate()
            bot_process.join()
        logger.info('Приложение остановлено')
