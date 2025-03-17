import asyncio
import logging.config
import pathlib
from asyncio import set_event_loop, new_event_loop
from multiprocessing import Process

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, BotCommandScopeAllPrivateChats
from aiogram_dialog import setup_dialogs
from flask import Flask
from flask_jwt_extended import JWTManager

from flask_cors import CORS
from fluent.runtime import FluentLocalization
from fluentogram import TranslatorHub

from backend.cache_config import cache
from backend.create_bot import main_bot, dp
from backend.dialogs.task_dialogs import task_dialog
from backend.dialogs.task_edit_dialog import task_edit_dialog
from backend.dialogs.task_list_dialog import task_list_dialog
from backend.handlers import task_handlers
from backend.i18n_factory import create_translator_hub
from backend.load_env import env_config
from backend.locale_config import i18n, get_user_locale, set_user_locale_cache, get_locale
from backend.middleware import TranslatorRunnerMiddleware

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
    
    # Запускаем фоновую задачу для проверки обновлений команд бота
    asyncio.create_task(check_bot_updates_task())

async def check_bot_updates_task():
    """Фоновая задача для проверки обновлений команд бота"""
    logger.info("Запущена фоновая задача проверки обновлений команд бота")
    
    while True:
        try:
            await check_and_update_bot_commands()
        except Exception as e:
            logger.exception(f"Ошибка при проверке обновлений команд бота: {e}")
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)

async def check_and_update_bot_commands():
    """Проверяет и обновляет команды бота для пользователей с флагом needs_bot_update"""
    from backend.database import get_session
    from backend.services.auth_service import AuthService
    
    async with get_session() as session:
        auth_service = AuthService(session)
        # Получаем пользователей, которым нужно обновить команды бота
        users = await auth_service.get_users_needing_bot_update()
        
        if not users:
            return
            
        logger.info(f"Найдено {len(users)} пользователей для обновления команд бота")
        
        # Если есть пользователи с обновлениями, обновляем также глобальные команды бота
        # Это нужно чтобы обновить меню для всех пользователей, так как настройки по умолчанию 
        # могут не меняться автоматически
        await set_commands(main_bot)
        logger.info("Обновлены глобальные команды бота")
        
        for user in users:
            try:
                # Получаем локализацию пользователя, с принудительным обновлением из БД
                user_locale = await get_user_locale(str(user.telegram_id))
                
                # Обновляем команды бота для пользователя
                await set_user_commands(main_bot, str(user.telegram_id), user_locale)
                logger.info(f"Обновлены команды бота для пользователя {user.telegram_id}")
                
                # Сбрасываем флаг needs_bot_update
                await auth_service.set_user_bot_update_flag(str(user.telegram_id), False)
            except Exception as e:
                logger.exception(f"Ошибка при обновлении команд бота для пользователя {user.telegram_id}: {e}")

# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands(bot: Bot):
    # Создаем команды на русском (по умолчанию)
    commands = [BotCommand(command='start', description=i18n.format_value("start_menu")),
                BotCommand(command='profile', description=i18n.format_value("my_profile_menu")),
                BotCommand(command='tasks', description=i18n.format_value("tasks-menu")),
                BotCommand(command='add_task', description=i18n.format_value("add-task-menu")),
                BotCommand(command='settings', description=i18n.format_value("settings_menu")),
                BotCommand(command='language', description=i18n.format_value("settings_language")),
                BotCommand(command='help', description=i18n.format_value("help-menu")),
                BotCommand(command='stop', description=i18n.format_value("stop_menu"))]
                
    # Устанавливаем команды для чата по умолчанию
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    
    # Дополнительно устанавливаем команды для английского языка
    # Это нужно для корректного отображения на старте до выбора языка пользователем
    en_locale = get_locale("en")
    commands_en = [BotCommand(command='start', description=en_locale.format_value("start_menu")),
                   BotCommand(command='profile', description=en_locale.format_value("my_profile_menu")),
                   BotCommand(command='tasks', description=en_locale.format_value("tasks-menu")),
                   BotCommand(command='add_task', description=en_locale.format_value("add-task-menu")),
                   BotCommand(command='settings', description=en_locale.format_value("settings_menu")),
                   BotCommand(command='language', description=en_locale.format_value("settings_language")),
                   BotCommand(command='help', description=en_locale.format_value("help-menu")),
                   BotCommand(command='stop', description=en_locale.format_value("stop_menu"))]

    # # Устанавливаем команды для пользователей с английским языком интерфейса
    try:
        await bot.set_my_commands(commands_en, BotCommandScopeAllPrivateChats(), language_code="en")
        logger.info("Установлены команды бота для английского языка")
    except Exception as e:
        logger.exception(f"Ошибка при установке команд бота для английского языка: {e}")

# Функция, которая выполнится когда бот завершит свою работу
async def stop_bot(bot: Bot):
    logger.info('Бот остановлен')

async def main():
    # Инициализируем базу данных
    from backend.database import init_db
    await init_db()
    
    # Регистрируем роутеры
    dp.include_router(task_handlers.router)
    translator_hub: TranslatorHub = create_translator_hub()
    dp.update.middleware(TranslatorRunnerMiddleware(translator_hub))

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
    
    commands = [
        BotCommand(command='start', description=user_locale.format_value("start_menu")),
        BotCommand(command='profile', description=user_locale.format_value("my_profile_menu")),
        BotCommand(command='tasks', description=user_locale.format_value("tasks-menu")),
        BotCommand(command='add_task', description=user_locale.format_value("add-task-menu")),
        BotCommand(command='settings', description=user_locale.format_value("settings_menu")),
        BotCommand(command='language', description=user_locale.format_value("settings_language")),
        BotCommand(command='help', description=user_locale.format_value("help-menu")),
        BotCommand(command='stop', description=user_locale.format_value("stop_menu"))
    ]
    
    try:
        # Устанавливаем команды для конкретного пользователя с учетом его языка
        scope = BotCommandScopeChat(chat_id=int(user_id))
        await bot.set_my_commands(commands, scope, language_code=language_code)
        logger.info(f"Установлены команды бота для пользователя {user_id} с языком {language_code}")
    except Exception as e:
        logger.exception(f"Ошибка при установке команд бота для пользователя {user_id}: {e}")
