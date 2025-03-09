import logging

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from backend.blueprints.wrapper import async_route
from backend.cache_config import cache
from backend.database import get_session
from backend.services.auth_service import AuthService


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

