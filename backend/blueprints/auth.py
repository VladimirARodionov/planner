from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from backend.cache_config import cache


bp = Blueprint("auth", __name__)

import logging
logging.basicConfig(filename="log_file.log", level=logging.DEBUG)


@bp.route('/api/auth/login/', methods=['OPTIONS', 'POST'])
@cross_origin()
def authenticate():
    if request.method == 'OPTIONS':
        return 200
    data = request.json
    allowed = True
    if allowed:
        access_token = create_access_token(identity=data['username'])
        refresh_token = create_refresh_token(identity=data['username'])
        cache.set("current_user_" + data['username'], data)
        return jsonify({'user': data['username'], 'access': access_token, 'refresh': refresh_token}), 200
    else:
        cache.delete("current_user_" + data['username'])
        return jsonify({'message': 'Error'}), 500


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

