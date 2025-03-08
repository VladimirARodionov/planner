from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database import get_session
from backend.db.models import (
    User, Task, StatusSetting, PrioritySetting, DurationSetting, DurationType
)

bp = Blueprint("planner", __name__)

# Маршруты для работы с задачами
@bp.route('/api/tasks/', methods=['GET'])
@cross_origin()
@jwt_required()
async def get_tasks():
    """Получить список задач пользователя"""
    current_user = get_jwt_identity()
    
    # Получаем параметры фильтрации
    status_id = request.args.get('status_id', type=int)
    priority_id = request.args.get('priority_id', type=int)
    duration_id = request.args.get('duration_id', type=int)
    is_completed = request.args.get('is_completed', type=bool, default=False)
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Формируем запрос с фильтрами
        query = select(Task).where(Task.user_id == user.id)
        
        if status_id:
            query = query.where(Task.status_id == status_id)
        if priority_id:
            query = query.where(Task.priority_id == priority_id)
        if duration_id:
            query = query.where(Task.duration_id == duration_id)
            
        # Загружаем связанные данные
        query = query.options(
            selectinload(Task.status),
            selectinload(Task.priority),
            selectinload(Task.duration)
        )
        
        tasks = await session.execute(query)
        tasks = tasks.scalars().all()
        
        # Преобразуем задачи в JSON
        tasks_data = [{
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': {
                'id': task.status.id,
                'name': task.status.name,
                'color': task.status.color
            } if task.status else None,
            'priority': {
                'id': task.priority.id,
                'name': task.priority.name,
                'color': task.priority.color
            } if task.priority else None,
            'duration': {
                'id': task.duration.id,
                'name': task.duration.name,
                'type': task.duration.duration_type.value,
                'value': task.duration.value
            } if task.duration else None,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'is_overdue': task.is_overdue()
        } for task in tasks]
        
        return jsonify({'tasks': tasks_data}), 200

@bp.route('/api/tasks/', methods=['POST'])
@cross_origin()
@jwt_required()
async def create_task():
    """Создать новую задачу"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Создаем задачу
        task = Task(
            user_id=user.id,
            title=data['title'],
            description=data.get('description'),
            status_id=data.get('status_id'),
            priority_id=data.get('priority_id'),
            duration_id=data.get('duration_id')
        )
        
        # Если указана продолжительность, рассчитываем дедлайн
        if task.duration_id:
            duration = await session.get(DurationSetting, task.duration_id)
            if duration:
                task.deadline = await duration.calculate_deadline_async()
        
        session.add(task)
        await session.commit()
        
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'created_at': task.created_at.isoformat()
        }), 201

@bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@cross_origin()
@jwt_required()
async def update_task(task_id):
    """Обновить задачу"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    async with get_session() as session:
        # Получаем пользователя и задачу
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        task = await session.get(Task, task_id)
        if not task or task.user_id != user.id:
            return jsonify({'error': 'Task not found'}), 404
        
        # Обновляем поля задачи
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'status_id' in data:
            task.status_id = data['status_id']
        if 'priority_id' in data:
            task.priority_id = data['priority_id']
        if 'duration_id' in data:
            task.duration_id = data['duration_id']
            # Пересчитываем дедлайн при изменении продолжительности
            duration = await session.get(DurationSetting, task.duration_id)
            if duration:
                task.deadline = await duration.calculate_deadline_async()
        
        await session.commit()
        
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'updated_at': task.updated_at.isoformat()
        }), 200

@bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@cross_origin()
@jwt_required()
async def delete_task(task_id):
    """Удалить задачу"""
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        # Получаем пользователя и задачу
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        task = await session.get(Task, task_id)
        if not task or task.user_id != user.id:
            return jsonify({'error': 'Task not found'}), 404
        
        await session.delete(task)
        await session.commit()
        
        return '', 204

# Маршруты для работы с настройками
@bp.route('/api/settings/', methods=['GET'])
@cross_origin()
@jwt_required()
async def get_settings():
    """Получить настройки пользователя"""
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Получаем настройки пользователя
        statuses = await session.execute(
            select(StatusSetting)
            .where(StatusSetting.user_id == user.id)
            .order_by(StatusSetting.order)
        )
        priorities = await session.execute(
            select(PrioritySetting)
            .where(PrioritySetting.user_id == user.id)
            .order_by(PrioritySetting.order)
        )
        durations = await session.execute(
            select(DurationSetting)
            .where(DurationSetting.user_id == user.id)
            .order_by(DurationSetting.value)
        )
        
        # Преобразуем настройки в JSON
        settings = {
            'statuses': [{
                'id': status.id,
                'name': status.name,
                'code': status.code,
                'color': status.color,
                'order': status.order,
                'is_active': status.is_active,
                'is_default': status.is_default,
                'is_final': status.is_final
            } for status in statuses.scalars()],
            'priorities': [{
                'id': priority.id,
                'name': priority.name,
                'color': priority.color,
                'order': priority.order,
                'is_active': priority.is_active,
                'is_default': priority.is_default
            } for priority in priorities.scalars()],
            'durations': [{
                'id': duration.id,
                'name': duration.name,
                'type': duration.duration_type.value,
                'value': duration.value,
                'is_active': duration.is_active,
                'is_default': duration.is_default
            } for duration in durations.scalars()]
        }
        
        return jsonify(settings), 200

@bp.route('/api/settings/<string:setting_type>/', methods=['POST'])
@cross_origin()
@jwt_required()
async def create_setting(setting_type):
    """Создать новую настройку"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Создаем настройку в зависимости от типа
        if setting_type == 'status':
            setting = StatusSetting(
                user_id=user.id,
                name=data['name'],
                code=data['code'],
                color=data.get('color', '#808080'),
                order=data.get('order', 0),
                is_active=data.get('is_active', True),
                is_default=data.get('is_default', False),
                is_final=data.get('is_final', False)
            )
        elif setting_type == 'priority':
            setting = PrioritySetting(
                user_id=user.id,
                name=data['name'],
                color=data.get('color', '#808080'),
                order=data.get('order', 0),
                is_active=data.get('is_active', True),
                is_default=data.get('is_default', False)
            )
        else:  # duration
            setting = DurationSetting(
                user_id=user.id,
                name=data['name'],
                duration_type=DurationType(data['type']),
                value=data['value'],
                is_active=data.get('is_active', True),
                is_default=data.get('is_default', False)
            )
        
        session.add(setting)
        await session.commit()
        
        return jsonify({
            'id': setting.id,
            'name': setting.name,
            'created_at': setting.created_at.isoformat()
        }), 201

@bp.route('/api/settings/<string:setting_type>/<int:setting_id>', methods=['PUT'])
@cross_origin()
@jwt_required()
async def update_setting(setting_type, setting_id):
    """Обновить настройку"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Получаем и обновляем настройку
        if setting_type == 'status':
            setting = await session.get(StatusSetting, setting_id)
            if not setting or setting.user_id != user.id:
                return jsonify({'error': 'Setting not found'}), 404
            
            if 'name' in data:
                setting.name = data['name']
            if 'code' in data:
                setting.code = data['code']
            if 'color' in data:
                setting.color = data['color']
            if 'order' in data:
                setting.order = data['order']
            if 'is_active' in data:
                setting.is_active = data['is_active']
            if 'is_default' in data:
                setting.is_default = data['is_default']
            if 'is_final' in data:
                setting.is_final = data['is_final']
                
        elif setting_type == 'priority':
            setting = await session.get(PrioritySetting, setting_id)
            if not setting or setting.user_id != user.id:
                return jsonify({'error': 'Setting not found'}), 404
            
            if 'name' in data:
                setting.name = data['name']
            if 'color' in data:
                setting.color = data['color']
            if 'order' in data:
                setting.order = data['order']
            if 'is_active' in data:
                setting.is_active = data['is_active']
            if 'is_default' in data:
                setting.is_default = data['is_default']
                
        else:  # duration
            setting = await session.get(DurationSetting, setting_id)
            if not setting or setting.user_id != user.id:
                return jsonify({'error': 'Setting not found'}), 404
            
            if 'name' in data:
                setting.name = data['name']
            if 'type' in data:
                setting.duration_type = DurationType(data['type'])
            if 'value' in data:
                setting.value = data['value']
            if 'is_active' in data:
                setting.is_active = data['is_active']
            if 'is_default' in data:
                setting.is_default = data['is_default']
        
        await session.commit()
        
        return jsonify({
            'id': setting.id,
            'name': setting.name,
            'updated_at': setting.updated_at.isoformat()
        }), 200

@bp.route('/api/settings/<string:setting_type>/<int:setting_id>', methods=['DELETE'])
@cross_origin()
@jwt_required()
async def delete_setting(setting_type, setting_id):
    """Удалить настройку"""
    current_user = get_jwt_identity()
    
    if setting_type not in ['status', 'priority', 'duration']:
        return jsonify({'error': 'Invalid setting type'}), 400
    
    async with get_session() as session:
        # Получаем пользователя
        user = await session.execute(
            select(User).where(User.telegram_id == current_user)
        )
        user = user.scalar_one_or_none()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Получаем и удаляем настройку
        setting_class = {
            'status': StatusSetting,
            'priority': PrioritySetting,
            'duration': DurationSetting
        }[setting_type]
        
        setting = await session.get(setting_class, setting_id)
        if not setting or setting.user_id != user.id:
            return jsonify({'error': 'Setting not found'}), 404
        
        await session.delete(setting)
        await session.commit()
        
        return '', 204
