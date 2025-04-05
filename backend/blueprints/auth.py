import logging
import secrets

from flask import Blueprint, request, jsonify, redirect
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from backend.blueprints.wrapper import async_route
from backend.cache_config import cache
from backend.database import get_session
from backend.locale_config import AVAILABLE_LANGUAGES
from backend.services.auth_service import AuthService
from backend.load_env import env_config


bp = Blueprint("auth", __name__)

logger = logging.getLogger(__name__)


@bp.route('/api/auth/login/', methods=['OPTIONS', 'POST'])
@cross_origin()
@async_route
async def authenticate():
    """Аутентифицировать пользователя"""
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    logger.info(f"Попытка аутентификации пользователя {username}")

    if not username or not password:
        logger.warning(f"Отсутствуют обязательные поля username или password")
        return jsonify({'error': 'Username and password are required'}), 400

    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.authenticate_user(username, password)
        
        if user:
            logger.info(f"Пользователь {username} успешно аутентифицирован")
            # Используем telegram_id пользователя в качестве идентификатора в токене
            access_token = create_access_token(identity=str(user.telegram_id))
            refresh_token = create_refresh_token(identity=str(user.telegram_id))
            logger.info(f"Созданы токены для пользователя {username} с идентификатором {user.telegram_id}")
            cache.set("current_user_" + username, data)
            return jsonify({
                'user': username,
                'access': access_token,
                'refresh': refresh_token
            }), 200
        else:
            logger.warning(f"Неверные учетные данные для пользователя {username}")
            cache.delete("current_user_" + username)
            return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/api/auth/refresh/', methods=['OPTIONS', 'POST'])
@cross_origin()
@jwt_required(refresh=True)
def refresh():
    """Обновить access токен с помощью refresh токена"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Получаем идентификатор пользователя из refresh токена
        current_user = get_jwt_identity()
        logger.info(f"Обновление токена для пользователя с идентификатором {current_user}")
        
        # Создаем новый access токен
        access_token = create_access_token(identity=current_user)
        logger.info(f"Создан новый access токен для пользователя с идентификатором {current_user}")
        
        return jsonify({
            'user': current_user,
            'access': access_token
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при обновлении токена: {e}")
        return jsonify({'error': 'Invalid refresh token'}), 401


@bp.route('/api/auth/logout/', methods=['OPTIONS', 'POST'])
@cross_origin()
def user_logout():
    current_user = request.json['user']
    cache.delete("current_user_" + current_user)
    return jsonify({'message': "success"}), 204


@bp.route('/api/auth/telegram/login', methods=['GET'])
@cross_origin()
@async_route
async def telegram_login():
    """Инициировать авторизацию через Telegram"""
    # Генерируем случайную строку для защиты от CSRF
    auth_state = secrets.token_hex(16)
    
    # Получаем redirect_url из параметров запроса или используем значение по умолчанию
    redirect_url = request.args.get('redirect_url', env_config.get('FRONTEND_URL', 'http://localhost:3000'))
    
    # Проверяем, содержит ли URL localhost, и заменяем его на публичный домен
    # Telegram не принимает URL с localhost в качестве параметра для кнопок
    if "localhost" in redirect_url:
        # В продакшене нужно заменить на реальный домен
        public_domain = env_config.get('PUBLIC_URL', 'http://127.0.0.1:3000')
        redirect_url = redirect_url.replace("http://localhost:3000", public_domain)
        logger.info(f"Заменен localhost URL на публичный домен: {redirect_url}")
    
    # Сохраняем состояние авторизации и URL для редиректа в базу данных
    async with get_session() as session:
        auth_service = AuthService(session)
        success = await auth_service.add_auth_state(auth_state, redirect_url)
    
    if not success:
        logger.error(f"Не удалось сохранить состояние авторизации {auth_state}")
        return jsonify({"error": "Failed to save authentication state"}), 500
    
    # Получаем данные для авторизации
    bot_username = env_config.get('TELEGRAM_BOT_USERNAME')
    
    # Формируем URL для перехода в Telegram бота
    telegram_auth_url = f"https://t.me/{bot_username}?start=auth_{auth_state}"
    
    logger.info(f"Redirecting to Telegram auth: {telegram_auth_url}")
    return redirect(telegram_auth_url)


@bp.route('/api/user/language', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_user_language():
    """Получить язык пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    # Получаем ID пользователя из JWT-токена
    user_id = get_jwt_identity()
    
    async with get_session() as session:
        auth_service = AuthService(session)
        language = await auth_service.get_user_language(user_id)
        
        return jsonify({
            'language': language
        }), 200

@bp.route('/api/user/language', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def set_user_language():
    """Установить язык пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    # Получаем ID пользователя из JWT-токена
    user_id = get_jwt_identity()
    
    # Получаем данные из запроса
    data = request.get_json()
    language = data.get('language')
    
    if not language:
        return jsonify({'error': 'Language is required'}), 400
        
    if language not in AVAILABLE_LANGUAGES:
        return jsonify({'error': 'Unsupported language'}), 400
    
    async with get_session() as session:
        auth_service = AuthService(session)
        success = await auth_service.set_user_language(user_id, language)
        
        if success:
            # Обновляем кеш локализации
            from backend.locale_config import set_user_locale
            set_success = set_user_locale(user_id, language)
            logger.debug(f"Обновление локализации пользователя {user_id} на {language} успешно: {set_success}")

            return jsonify({
                'message': 'Language updated successfully',
                'language': language
            }), 200
        else:
            return jsonify({'error': 'Failed to update language'}), 500


@bp.route('/api/user/timezone', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_user_timezone():
    """Получение часового пояса пользователя."""
    if request.method == 'OPTIONS':
        return '', 200
    
    user_id = get_jwt_identity()
    
    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.get_user_by_id(user_id)
        
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({'timezone': user.timezone})

@bp.route('/api/user/timezone', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def update_user_timezone():
    """Обновление часового пояса пользователя."""
    if request.method == 'OPTIONS':
        return '', 200
    
    user_id = get_jwt_identity()
    data = request.get_json()
    timezone = data.get('timezone')
    
    if not timezone:
        return jsonify({'error': 'Timezone is required'}), 400
    
    async with get_session() as session:
        auth_service = AuthService(session)
        success = await auth_service.update_user_timezone(user_id, timezone)
        
    if not success:
        return jsonify({'error': 'Failed to update timezone'}), 500
        
    return '', 201

@bp.route('/api/timezones', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_available_timezones():
    """Получение списка доступных часовых поясов."""
    if request.method == 'OPTIONS':
        return '', 200
    
    import pytz
    timezones = [
        {
            'value': tz,
            'label': tz.replace('_', ' '),
            'group': tz.split('/', 1)[0] if '/' in tz else 'Other'
        }
        for tz in pytz.all_timezones
    ]
    
    return jsonify(timezones)

