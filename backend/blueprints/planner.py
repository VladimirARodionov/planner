import logging
from datetime import datetime

import pytz
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.blueprints.wrapper import async_route
from backend.database import get_session
from backend.services.task_service import TaskService
from backend.services.settings_service import SettingsService
from backend.db.models import DurationSetting, User

bp = Blueprint("planner", __name__)
logger = logging.getLogger(__name__)

def process_deadline_filter(deadline_str, is_from=True):
    """Преобразуем строку даты в формат ISO для фильтрации задач по дедлайну"""
    try:
        # Преобразуем строку в дату, если она не в формате YYYY-MM-DD
        if 'T' in deadline_str:
            deadline_str = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date().isoformat()
        return deadline_str
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting deadline_{'from' if is_from else 'to'}: {e}")
        return deadline_str

# Маршруты для работы с задачами
@bp.route('/api/tasks/<int:task_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_task(task_id):
    if request.method == 'OPTIONS':
        return '', 200
    """Получить задачу по ID"""
    user_id = get_jwt_identity()

    async with get_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.get_tasks(user_id, {'id': task_id})

    if tasks and len(tasks) > 0:
        return jsonify(tasks[0])
    else:
        return jsonify({'error': 'Task not found'}), 404


@bp.route('/api/tasks/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_tasks():
    """Получить список задач пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Добавляем отладочную информацию
    logger.info(f"Получен запрос на получение задач")
    logger.info(f"Заголовки запроса: {request.headers}")
    
    try:
        current_user = get_jwt_identity()
        logger.info(f"Идентификатор пользователя из токена: {current_user}")

        # Получаем параметры фильтрации из запроса
        filters = {}
        if request.args.get('status_id'):
            filters['status_id'] = int(request.args.get('status_id'))
        if request.args.get('priority_id'):
            filters['priority_id'] = int(request.args.get('priority_id'))
        if request.args.get('duration_id'):
            filters['duration_id'] = int(request.args.get('duration_id'))
        if request.args.get('type_id'):
            filters['type_id'] = int(request.args.get('type_id'))
        if 'is_completed' in request.args:
            # Преобразуем строковое значение 'true'/'false' в булево
            is_completed_str = request.args.get('is_completed').lower()
            filters['is_completed'] = is_completed_str == 'true'
        
        # Добавляем фильтрацию по дедлайну
        if request.args.get('deadline_from'):
            deadline_from = request.args.get('deadline_from')
            filters['deadline_from'] = process_deadline_filter(deadline_from)
        
        if request.args.get('deadline_to'):
            deadline_to = request.args.get('deadline_to')
            filters['deadline_to'] = process_deadline_filter(deadline_to, False)

        async with get_session() as session:
            task_service = TaskService(session)
            tasks = await task_service.get_tasks(current_user, filters)
            logger.info(f"Получены задачи: {tasks}")
            return jsonify({'tasks': tasks})
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tasks/paginated', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_tasks_paginated():
    if request.method == 'OPTIONS':
        return '', 200
    """Получить список задач пользователя с пагинацией, сортировкой и поиском"""
    user_id = get_jwt_identity()

    # Получаем параметры пагинации из запроса
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))

    # Получаем параметры сортировки из запроса
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order', 'asc')

    # Получаем параметр поиска из запроса
    search_query = request.args.get('search')

    # Получаем параметры фильтрации из запроса
    filters = {}
    if request.args.get('status_id'):
        filters['status_id'] = int(request.args.get('status_id'))
    if request.args.get('priority_id'):
        filters['priority_id'] = int(request.args.get('priority_id'))
    if request.args.get('duration_id'):
        filters['duration_id'] = int(request.args.get('duration_id'))
    if request.args.get('type_id'):
        filters['type_id'] = int(request.args.get('type_id'))
    if 'is_completed' in request.args:
        # Преобразуем строковое значение 'true'/'false' в булево
        is_completed_str = request.args.get('is_completed').lower()
        filters['is_completed'] = is_completed_str == 'true'
    
    # Добавляем фильтрацию по дедлайну
    if request.args.get('deadline_from'):
        deadline_from = request.args.get('deadline_from')
        filters['deadline_from'] = process_deadline_filter(deadline_from)
        
    if request.args.get('deadline_to'):
        deadline_to = request.args.get('deadline_to')
        filters['deadline_to'] = process_deadline_filter(deadline_to, False)

    async with get_session() as session:
        task_service = TaskService(session)
        tasks, total_tasks = await task_service.get_tasks_paginated(
            user_id,
            page,
            page_size,
            filters,
            sort_by,
            sort_order,
            search_query
        )

        # Вычисляем общее количество страниц
        total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 0

        response = {
            'tasks': tasks,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_tasks': total_tasks,
                'total_pages': total_pages
            }
        }

    return jsonify(response)

@bp.route('/api/tasks/search', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def search_tasks():
    if request.method == 'OPTIONS':
        return '', 200
    """Поиск задач по названию и описанию"""
    user_id = get_jwt_identity()

    # Получаем параметр поиска из запроса
    search_query = request.args.get('q', '')

    # Получаем параметры фильтрации из запроса
    filters = {}
    if request.args.get('status_id'):
        filters['status_id'] = int(request.args.get('status_id'))
    if request.args.get('priority_id'):
        filters['priority_id'] = int(request.args.get('priority_id'))
    if request.args.get('duration_id'):
        filters['duration_id'] = int(request.args.get('duration_id'))
    if request.args.get('type_id'):
        filters['type_id'] = int(request.args.get('type_id'))
    if 'is_completed' in request.args:
        # Преобразуем строковое значение 'true'/'false' в булево
        is_completed_str = request.args.get('is_completed').lower()
        filters['is_completed'] = is_completed_str == 'true'
    
    # Добавляем фильтрацию по дедлайну
    if request.args.get('deadline_from'):
        deadline_from = request.args.get('deadline_from')
        filters['deadline_from'] = process_deadline_filter(deadline_from)
        
    if request.args.get('deadline_to'):
        deadline_to = request.args.get('deadline_to')
        filters['deadline_to'] = process_deadline_filter(deadline_to, False)

    async with get_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.search_tasks(user_id, search_query, filters)

    return jsonify(tasks)

@bp.route('/api/tasks/count', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_task_count():
    if request.method == 'OPTIONS':
        return '', 200
    """Получить общее количество задач пользователя с учетом фильтров и поиска"""
    user_id = get_jwt_identity()

    # Получаем параметр поиска из запроса
    search_query = request.args.get('search')

    # Получаем параметры фильтрации из запроса
    filters = {}
    if request.args.get('status_id'):
        filters['status_id'] = int(request.args.get('status_id'))
    if request.args.get('priority_id'):
        filters['priority_id'] = int(request.args.get('priority_id'))
    if request.args.get('duration_id'):
        filters['duration_id'] = int(request.args.get('duration_id'))
    if request.args.get('type_id'):
        filters['type_id'] = int(request.args.get('type_id'))
    if 'is_completed' in request.args:
        # Преобразуем строковое значение 'true'/'false' в булево
        is_completed_str = request.args.get('is_completed').lower()
        filters['is_completed'] = is_completed_str == 'true'
    
    # Добавляем фильтрацию по дедлайну
    if request.args.get('deadline_from'):
        deadline_from = request.args.get('deadline_from')
        filters['deadline_from'] = process_deadline_filter(deadline_from)
        
    if request.args.get('deadline_to'):
        deadline_to = request.args.get('deadline_to')
        filters['deadline_to'] = process_deadline_filter(deadline_to, False)

    async with get_session() as session:
        task_service = TaskService(session)
        count = await task_service.get_task_count(user_id, filters, search_query)

    return jsonify({'count': count})

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

@bp.route('/api/settings/duration/<int:duration_id>/calculate-deadline', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def calculate_deadline(duration_id):
    """Рассчитать дедлайн на основе длительности"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        try:
            user = await session.get(User, current_user)
            duration = await session.get(DurationSetting, duration_id)
            
            # Проверяем, принадлежит ли длительность пользователю
            if not duration or str(duration.user_id) != current_user:
                return jsonify({'error': 'Duration not found'}), 404
                
            # Получаем начальную дату из запроса или используем текущую дату и время
            from_date = datetime.now(tz=pytz.timezone(user.timezone))  # По умолчанию используем текущую дату и время
            if request.args.get('from_date'):
                try:
                    from_date = datetime.fromisoformat(
                        request.args.get('from_date').replace('Z', '+00:00')
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing from_date: {e}")
                    # Если не удалось распарсить дату из запроса, продолжаем использовать текущую дату и время
            
            # Расчитываем дедлайн
            deadline = await duration.calculate_deadline_async(session, from_date)
            
            return jsonify({
                'deadline': deadline.isoformat() if deadline else None
            })
        except Exception as e:
            logger.error(f"Error calculating deadline: {e}")
            return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/priority/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_priorities():
    """Получить список приоритетов пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    logger.debug(f"Получение приоритетов для пользователя {current_user}")
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        priorities = await settings_service.get_priorities(current_user)
        logger.debug(f"Найдено {len(priorities)} приоритетов")
        return jsonify(priorities)


@bp.route('/api/settings/status/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_statuses():
    """Получить список статусов пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        statuses = await settings_service.get_statuses(current_user)
        return jsonify(statuses)


@bp.route('/api/settings/duration/', methods=['GET', 'OPTIONS'])
@cross_origin()
@jwt_required()
@async_route
async def get_durations():
    """Получить список длительностей пользователя"""
    if request.method == 'OPTIONS':
        return '', 200
        
    current_user = get_jwt_identity()
    
    async with get_session() as session:
        settings_service = SettingsService(session)
        durations = await settings_service.get_durations(current_user)
        return jsonify(durations)
