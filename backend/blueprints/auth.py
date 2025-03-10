import logging
import secrets

from flask import Blueprint, request, jsonify, redirect
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from backend.blueprints.wrapper import async_route
from backend.cache_config import cache
from backend.database import get_session
from backend.services.auth_service import AuthService
from backend.load_env import env_config
from backend.handlers.task_handlers import add_auth_state


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

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    async with get_session() as session:
        auth_service = AuthService(session)
        user = await auth_service.authenticate_user(username, password)
        
        if user:
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)
            cache.set("current_user_" + username, data)
            return jsonify({
                'user': username,
                'access': access_token,
                'refresh': refresh_token
            }), 200
        else:
            cache.delete("current_user_" + username)
            return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/api/auth/refresh/', methods=['OPTIONS', 'POST'])
@cross_origin()
@jwt_required()
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return jsonify({'user': current_user, 'access': access_token}), 200


@bp.route('/api/auth/logout/', methods=['OPTIONS', 'POST'])
@cross_origin()
def user_logout():
    current_user = request.json['user']
    cache.delete("current_user_" + current_user)
    return jsonify({'message': "success"}), 204


@bp.route('/api/auth/telegram/login', methods=['GET'])
@cross_origin()
def telegram_login():
    """Инициировать авторизацию через Telegram"""
    # Генерируем случайную строку для защиты от CSRF
    auth_state = secrets.token_hex(16)
    
    # Получаем redirect_url из параметров запроса или используем значение по умолчанию
    redirect_url = request.args.get('redirect_url', env_config.get('FRONTEND_URL', 'http://localhost:3000'))
    
    # Проверяем, содержит ли URL localhost, и заменяем его на публичный домен
    # Telegram не принимает URL с localhost в качестве параметра для кнопок
    if "localhost" in redirect_url:
        # В продакшене нужно заменить на реальный домен
        public_domain = env_config.get('PUBLIC_DOMAIN', 'https://viewstore-planner.example.com')
        redirect_url = redirect_url.replace("http://localhost:3000", public_domain)
        logger.info(f"Заменен localhost URL на публичный домен: {redirect_url}")
    
    # Сохраняем состояние авторизации и URL для редиректа
    add_auth_state(auth_state, redirect_url)
    
    # Получаем данные для авторизации
    bot_username = env_config.get('TELEGRAM_BOT_USERNAME')
    
    # Формируем URL для перехода в Telegram бота
    telegram_auth_url = f"https://t.me/{bot_username}?start=auth_{auth_state}"
    
    logger.info(f"Redirecting to Telegram auth: {telegram_auth_url}")
    return redirect(telegram_auth_url)

