import asyncio
import logging.config
import os
import pathlib
from asyncio import set_event_loop, new_event_loop
from multiprocessing import Process

from aiogram import Bot
from aiogram.types import BotCommandScopeDefault, BotCommandScopeChat, BotCommandScopeAllPrivateChats
from aiogram_dialog import setup_dialogs
from alembic import command
from alembic.config import Config
from flask import Flask
from flask_jwt_extended import JWTManager

from flask_cors import CORS
from fluent.runtime import FluentLocalization
from fluentogram import TranslatorHub

from backend.cache_config import cache
from backend.create_bot import main_bot, dp, get_bot_commands, ENVIRONMENT
from backend.dialogs.task_dialogs import task_dialog
from backend.dialogs.task_edit_dialog import task_edit_dialog
from backend.dialogs.task_list_dialog import task_list_dialog
from backend.handlers import task_handlers
from backend.i18n_factory import create_translator_hub
from backend.load_env import env_config
from backend.locale_config import set_user_locale_cache, get_locale, AVAILABLE_LANGUAGES
from backend.middleware import TranslatorRunnerMiddleware

if os.getenv('RUN_BOT') == "0":
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes['configure_logger'] = False
    command.upgrade(alembic_cfg, "head")

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
    # Создаем область видимости команд по умолчанию
    default_scope = BotCommandScopeDefault()

    # Устанавливаем команды для чата по умолчанию
    await bot.set_my_commands(get_bot_commands(), default_scope)
    logger.debug("Установлены глобальные команды бота на русском языке")

    # Устанавливаем команды для всех приватных чатов на русском языке
    all_private_scope = BotCommandScopeAllPrivateChats()
    await bot.set_my_commands(get_bot_commands(), all_private_scope, language_code="ru")
    logger.debug("Установлены команды бота для всех приватных чатов на русском языке")

    # Дополнительно устанавливаем команды для английского языка
    # Это нужно для корректного отображения на старте до выбора языка пользователем
    en_locale = get_locale("en")
    # Устанавливаем команды для пользователей с английским языком интерфейса
    try:
        await bot.set_my_commands(get_bot_commands(en_locale), all_private_scope, language_code="en")
        logger.info("Установлены команды бота для английского языка")
    except Exception as e:
        logger.exception(f"Ошибка при установке команд бота для английского языка: {e}")

# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot(bot: Bot):
    logger.info('Бот остановлен')

async def main():
    """Основная функция запуска бота"""
    # Инициализируем базу данных
    from backend.database import init_db
    await init_db()

    # Регистрируем роутеры
    dp.include_router(task_handlers.router)
    #translator_hub: TranslatorHub = create_translator_hub()
    #dp.update.middleware(TranslatorRunnerMiddleware(translator_hub))

    dp.include_router(task_dialog)
    dp.include_router(task_list_dialog)
    dp.include_router(task_edit_dialog)
    # Регистрируем диалоги
    setup_dialogs(dp)

    # регистрация функций
    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    logger.info('Бот запущен.')
    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        logger.info("Удаление webhook и старт polling...")
        # Увеличиваем таймаут для операций с API Telegram
        await main_bot.delete_webhook(drop_pending_updates=True)
        if ENVIRONMENT == "DEVELOPMENT":
            set_event_loop(new_event_loop())
        await dp.start_polling(main_bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
    finally:
        try:
            if not main_bot.session.closed:
                await main_bot.session.close()
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессии бота: {e}")
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
                 "origins": ["http://localhost:3000", env_config.get('FRONTEND_URL'), env_config.get('PUBLIC_URL')],
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
    from backend.blueprints import auth_bp, planner_bp, settings_bp, health_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(health_bp)

    jwt = JWTManager(app)
    app.debug = True
    return app, jwt


def run_flask(app):
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

if __name__ == '__main__':
    # Создаем приложение Flask
    app, jwt = create_app()
    try:
        if ENVIRONMENT == "DEVELOPMENT":
            # Запускаем бота в отдельном процессе
            bot_process = start_process_aiogram()
            # Запускаем Flask в основном процессе
            run_flask(app)
        elif os.getenv('RUN_BOT') == "1":
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Клавиатурное прерывание')
    except asyncio.CancelledError:
        logger.info('Прерывание')
    finally:
        if ENVIRONMENT == "DEVELOPMENT":
            # Завершаем процесс бота при выходе
            if bot_process.is_alive():
                bot_process.terminate()
                bot_process.join()
        logger.info('Приложение остановлено')

async def set_user_commands(bot: Bot, user_id: str, user_locale: FluentLocalization):
    """Устанавливает список команд бота для конкретного пользователя"""
    # Обновляем локализацию в кеше
    set_user_locale_cache(user_id, user_locale)
    logger.debug(f"Обновлены локализации для пользователя {user_id} в кэше на {user_locale.locales}")

    # Определяем язык пользователя
    from backend.database import get_session
    from backend.services.auth_service import AuthService

    language_code = "ru"  # Значение по умолчанию

    try:
        async with get_session() as session:
            auth_service = AuthService(session)
            language_code = await auth_service.get_user_language(user_id)
            logger.debug(f"Получен язык {language_code} для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при получении языка пользователя {user_id}: {e}")

    try:
        # Преобразуем ID пользователя в число
        chat_id = int(user_id)
        scope = BotCommandScopeChat(chat_id=chat_id)

        # Сначала без указания языка
        await bot.set_my_commands(get_bot_commands(), scope=scope)
        logger.debug(f"Установлены команды бота для пользователя {user_id} без указания языка")

        # Затем с указанием языка
        for lang_code in AVAILABLE_LANGUAGES:
            await bot.set_my_commands(get_bot_commands(), scope=scope, language_code=lang_code)
            await bot.set_my_commands(get_bot_commands(), scope=scope, language_code=lang_code)
        logger.info(f"Установлены команды бота для пользователя {user_id} с языками {AVAILABLE_LANGUAGES}")
    except Exception as e:
        logger.exception(f"Ошибка при установке команд бота для пользователя {user_id}: {e}")

def create_app_wsgi():
    """Создание Flask приложения для запуска через Gunicorn"""
    app, _ = create_app()
    
    return app
