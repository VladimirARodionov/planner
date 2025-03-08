from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.cache_config import cache

bp = Blueprint("planner", __name__)

@bp.route('/api/planner/', methods=['OPTIONS', 'GET'])
@cross_origin()
@jwt_required()
def planner():
    if request.method == 'OPTIONS':
        return 200
    current_user = get_jwt_identity()
    data = cache.get("current_user_" + current_user)
    print(data)
    return jsonify({'data': data}), 200
