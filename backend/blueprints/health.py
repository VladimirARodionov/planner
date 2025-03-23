import logging

from flask import Blueprint, jsonify
from flask_cors import cross_origin

bp = Blueprint("health", __name__)

logger = logging.getLogger(__name__)


@bp.route('/api/health', methods=['GET', 'OPTIONS'])
@cross_origin()
def health_check():
    """Эндпоинт для проверки работоспособности API в Docker healthcheck"""
    logger.debug("Health check requested")
    return jsonify({"status": "ok", "message": "API is up and running"}), 200 