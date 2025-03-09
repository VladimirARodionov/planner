import logging

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.blueprints.wrapper import async_route
from backend.database import get_session
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService

bp = Blueprint("planner", __name__)
logger = logging.getLogger(__name__)

# Маршруты для работы с задачами
@bp.route('/api/tasks/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_tasks():
    """Получить список задач пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    filters = {
        'status_id': request.args.get('status_id', type=int),
        'priority_id': request.args.get('priority_id', type=int),
        'duration_id': request.args.get('duration_id', type=int),
        'is_completed': request.args.get('is_completed', type=bool, default=False)
    }
    
    async with get_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.get_tasks(current_user, filters)
        return jsonify({'tasks': tasks})

@bp.route('/api/tasks/', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def create_task():
    """Создать новую задачу"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    task_data = request.get_json()
    
    async with get_session() as session:
        task_service = TaskService(session)
        task = await task_service.create_task(current_user, task_data)
        if not task:
            return jsonify({'error': 'Failed to create task'}), 400
        return jsonify(task), 201

@bp.route('/api/tasks/<int:task_id>', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def update_task(task_id):
    """Обновить задачу"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    task_data = request.get_json()
    
    async with get_session() as session:
        task_service = TaskService(session)
        task = await task_service.update_task(current_user, task_id, task_data)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task)

@bp.route('/api/tasks/<int:task_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def delete_task(task_id):
    """Удалить задачу"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        task_service = TaskService(session)
        success = await task_service.delete_task(current_user, task_id)
        if not success:
            return jsonify({'error': 'Task not found'}), 404
        return '', 204

# Маршруты для работы с настройками
@bp.route('/api/settings/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_settings():
    """Получить все настройки"""
    if request.method == 'OPTIONS':
        return '', 200
        
    async with get_session() as session:
        settings_service = SettingsService(session)
        settings = await settings_service.get_settings()
        return jsonify(settings)

@bp.route('/api/settings/<string:setting_type>/', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def create_setting(setting_type):
    """Создать новую настройку"""
    if request.method == 'OPTIONS':
        return '', 200
        
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    current_user = get_jwt_identity()
    setting_data = request.get_json()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        setting = await settings_service.create_setting(current_user, setting_type, setting_data)
        if not setting:
            return jsonify({'error': 'Failed to create setting'}), 400
        return jsonify(setting), 201

@bp.route('/api/settings/<string:setting_type>/<int:setting_id>', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def update_setting(setting_type, setting_id):
    """Обновить настройку"""
    if request.method == 'OPTIONS':
        return '', 200
        
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    current_user = get_jwt_identity()
    setting_data = request.get_json()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        setting = await settings_service.update_setting(current_user, setting_type, setting_id, setting_data)
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        return jsonify(setting)

@bp.route('/api/settings/<string:setting_type>/<int:setting_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def delete_setting(setting_type, setting_id):
    """Удалить настройку"""
    if request.method == 'OPTIONS':
        return '', 200
        
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        success = await settings_service.delete_setting(current_user, setting_type, setting_id)
        if not success:
            return jsonify({'error': 'Setting not found'}), 404
        return '', 204

# Маршруты для работы с типами задач
@bp.route('/api/settings/task-types/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_task_types():
    """Получить список типов задач пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_types = await settings_service.get_task_types(current_user)
        return jsonify(task_types)

@bp.route('/api/settings/task-types/', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def create_task_type():
    """Создать новый тип задачи"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    task_type_data = request.get_json()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_type = await settings_service.create_task_type(current_user, task_type_data)
        if not task_type:
            return jsonify({'error': 'Failed to create task type'}), 400
        return jsonify(task_type), 201

@bp.route('/api/settings/task-types/<int:task_type_id>', methods=['PUT', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def update_task_type(task_type_id):
    """Обновить тип задачи"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    task_type_data = request.get_json()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        task_type = await settings_service.update_task_type(current_user, task_type_id, task_type_data)
        if not task_type:
            return jsonify({'error': 'Task type not found'}), 404
        return jsonify(task_type)

@bp.route('/api/settings/task-types/<int:task_type_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def delete_task_type(task_type_id):
    """Удалить тип задачи"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        success = await settings_service.delete_task_type(current_user, task_type_id)
        if not success:
            return jsonify({'error': 'Task type not found'}), 404
        return '', 204
