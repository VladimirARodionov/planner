import logging

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.blueprints.wrapper import async_route
from backend.database import get_session
from backend.services.settings_service import SettingsService

bp = Blueprint("settings", __name__)
logger = logging.getLogger(__name__)

# Маршрут для получения пользовательских настроек
@bp.route('/api/user-preferences/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_user_preferences():
    """Получение настроек пользователя."""
    if request.method == 'OPTIONS':
        return '', 200
    user_id = get_jwt_identity()

    # Получаем пользователя из базы данных
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_user_settings(user_id)

    # Получаем настройки пользователя или возвращаем пустые
    user_settings = settings if settings else {
        "filters": {},
        "sort_by": "deadline",
        "sort_order": "asc"
    }

    return jsonify(user_settings)
    #return '', 200


# Маршрут для сохранения пользовательских настроек
@bp.route('/api/user-preferences/', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def save_user_preferences(preferences: dict):
    """Сохранение настроек пользователя."""
    if request.method == 'OPTIONS':
        return '', 200
    user_id = get_jwt_identity()

    # Получаем пользователя из базы данных
    async with get_session() as session:
        settings_service = SettingsService(session)
        success = await settings_service.save_user_preferences(user_id, preferences)

    if not success:
        return jsonify({'error': 'Failed to set setting'}), 500
    return '', 201
