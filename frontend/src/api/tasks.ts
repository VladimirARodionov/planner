import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { Task, Settings, Status, Priority, Duration, TaskType, DurationType } from '../types/task';
import { AuthAPI } from './auth';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Добавляем токен к каждому запросу
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Перехватчик ответов для обработки ошибок авторизации
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config;
        
        // Если ошибка 401 (Unauthorized) и это не запрос на обновление токена
        if (error.response?.status === 401 && 
            originalRequest && 
            !(originalRequest.url === '/auth/refresh/')) {
            
            try {
                // Пытаемся обновить токен
                await AuthAPI.refreshToken();
                
                // Повторяем исходный запрос с новым токеном
                const token = localStorage.getItem('token');
                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                
                return axios(originalRequest);
            } catch (refreshError) {
                // Если не удалось обновить токен, перенаправляем на страницу входа
                console.error('Failed to refresh token:', refreshError);
                localStorage.removeItem('token');
                localStorage.removeItem('refreshToken');
                localStorage.removeItem('user');
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }
        
        return Promise.reject(error);
    }
);

export interface CreateTaskDto {
    title: string;
    description?: string | null;
    type_id?: number;
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
    deadline?: string;
    completed?: boolean;
}

export interface UpdateTaskDto {
    title?: string;
    description?: string | null;
    type_id?: number;
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
    deadline?: string;
    completed?: boolean;
}

export interface TaskFilters {
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
    type_id?: number;
    is_completed?: boolean;
    deadline_from?: string;
    deadline_to?: string;
}

export interface PaginationParams {
    page: number;
    page_size: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    search?: string;
}

export interface PaginatedResponse {
    tasks: Task[];
    pagination: {
        page: number;
        page_size: number;
        total_tasks: number;
        total_pages: number;
    };
}

export interface UserPreferences {
    filters: TaskFilters;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
}


export const TasksAPI = {
    // Задачи
    getTasks: async (filters?: TaskFilters) => {
        const response = await api.get<{ tasks: Task[] }>('/tasks/', { params: filters });
        return response.data.tasks;
    },

    // Получить список задач с пагинацией, сортировкой и поиском
    getTasksPaginated: async (
        pagination: PaginationParams,
        filters?: TaskFilters
    ) => {
        const response = await api.get<PaginatedResponse>('/tasks/paginated', {
            params: {
                ...pagination,
                ...filters
            }
        });
        return response.data;
    },

    // Поиск задач по названию и описанию
    searchTasks: async (
        query: string,
        filters?: TaskFilters
    ) => {
        const response = await api.get<{ tasks: Task[] }>('/tasks/search', {
            params: {
                q: query,
                ...filters
            }
        });
        return response.data.tasks;
    },

    // Получить общее количество задач с учетом фильтров и поиска
    getTaskCount: async (
        filters?: TaskFilters,
        search?: string
    ) => {
        const response = await api.get<{ count: number }>('/tasks/count', {
            params: {
                ...filters,
                search
            }
        });
        return response.data.count;
    },

    // Получить задачу по ID
    getTask: async (taskId: number): Promise<Task> => {
        const response = await api.get<Task>(`/tasks/${taskId}`);
        return response.data;
    },

    // Создать задачу
    createTask: async (task: CreateTaskDto) => {
        const response = await api.post<Task>('/tasks/', task);
        return response.data;
    },

    // Обновить задачу
    updateTask: async (taskId: number, task: UpdateTaskDto) => {
        const response = await api.put<Task>(`/tasks/${taskId}`, task);
        return response.data;
    },

    // Удалить задачу
    deleteTask: async (taskId: number) => {
        await api.delete(`/tasks/${taskId}`);
    },

    // Настройки
    getSettings: async () => {
        const response = await api.get<Settings>('/settings/');
        // Преобразуем duration_type в type, если нужно
        if (response.data.durations) {
            console.log('Raw durations from API:', response.data.durations);
            response.data.durations = response.data.durations.map(duration => {
                // Если тип не определен, но есть duration_type
                if ((!duration.type || typeof duration.type === 'undefined') && duration.duration_type) {
                    console.log(`Converting duration ${duration.name}: duration_type=${duration.duration_type} to type`);
                    return {
                        ...duration,
                        type: duration.duration_type as unknown as DurationType
                    };
                }
                return duration;
            });
            console.log('Processed durations:', response.data.durations);
        }
        return response.data;
    },

    // Типы задач
    getTaskTypes: async () => {
        const response = await api.get<TaskType[]>('/settings/task-types/');
        return response.data;
    },

    createStatus: async (status: {
        name: string;
        code: string;
        color?: string;
        order?: number;
        is_active?: boolean;
        is_default?: boolean;
        is_final?: boolean;
    }) => {
        const response = await api.post<Status>('/settings/status/', status);
        return response.data;
    },

    // Приоритеты
    getPriorities: async () => {
        const response = await api.get<Priority[]>('/settings/priority/');
        return response.data;
    },

    createPriority: async (priority: { name: string; color: string; position?: number; is_active?: boolean; is_default?: boolean }) => {
        const response = await api.post<Priority>('/settings/priority/', priority);
        return response.data;
    },

    updatePriority: async (id: number, priority: { name?: string; color?: string; position?: number; is_active?: boolean; is_default?: boolean }) => {
        const response = await api.put<Priority>(`/settings/priority/${id}`, priority);
        return response.data;
    },

    deletePriority: async (id: number) => {
        await api.delete(`/settings/priority/${id}`);
    },

    createDuration: async (duration: {
        name: string;
        type: string;
        value: number;
        is_active?: boolean;
        is_default?: boolean;
    }) => {
        const response = await api.post<Duration>('/settings/duration/', duration);
        return response.data;
    },

    updateStatus: async (statusId: number, status: Partial<Status>) => {
        const response = await api.put<Status>(`/settings/status/${statusId}`, status);
        return response.data;
    },

    deleteStatus: async (statusId: number) => {
        await api.delete(`/settings/status/${statusId}`);
    },

    updateDuration: async (durationId: number, duration: Partial<Duration>) => {
        const response = await api.put<Duration>(`/settings/duration/${durationId}`, duration);
        return response.data;
    },

    deleteDuration: async (durationId: number) => {
        await api.delete(`/settings/duration/${durationId}`);
    },

    createTaskType: async (taskType: {
        name: string;
        color?: string;
        is_active?: boolean;
        is_default?: boolean;
    }) => {
        const response = await api.post<TaskType>('/settings/task-types/', taskType);
        return response.data;
    },

    updateTaskType: async (taskTypeId: number, taskType: Partial<TaskType>) => {
        const response = await api.put<TaskType>(`/settings/task-types/${taskTypeId}`, taskType);
        return response.data;
    },

    deleteTaskType: async (taskTypeId: number) => {
        await api.delete(`/settings/task-types/${taskTypeId}`);
    },

    // Рассчитать дедлайн на основе длительности
    calculateDeadline: async (durationId: number, fromDate?: Date) => {
        let url = `/settings/duration/${durationId}/calculate-deadline`;
        
        console.log(`Calculating deadline for duration ID: ${durationId}`);
        
        // Если передана начальная дата, добавляем ее в запрос
        if (fromDate) {
            url += `?from_date=${fromDate.toISOString()}`;
            console.log(`Using custom from_date: ${fromDate.toISOString()}`);
        }
        
        console.log(`Making API request to: ${url}`);
        
        try {
            const response = await api.get<{ deadline: string }>(url);
            console.log('API response for deadline calculation:', response.data);
            return response.data.deadline ? new Date(response.data.deadline) : null;
        } catch (error) {
            console.error('Error calculating deadline:', error);
            throw error;
        }
    }
};

export const SettingsAPI = {
    getUserPreferences: async (): Promise<UserPreferences> => {
        try {
            const response = await api.get('/user-preferences/');
            return JSON.parse(response.data);
        } catch (error) {
            console.error('Error getting user preferences:', error);
            // Возвращаем значения по умолчанию
            return {
                filters: { is_completed: false },
                sort_by: 'deadline',
                sort_order: 'asc'
            };
        }
    },
    
    saveUserPreferences: async (preferences: UserPreferences): Promise<void> => {
        try {
            // Убедимся, что у нас есть валидный объект предпочтений
            const validPreferences: UserPreferences = {
                filters: preferences.filters || {},
                sort_by: preferences.sort_by || 'deadline',
                sort_order: preferences.sort_order || 'asc'
            };
            
            console.log('Saving preferences to API:', validPreferences);
            await api.post('/user-preferences/', validPreferences);
        } catch (error) {
            console.error('Error saving user preferences:', error);
            throw error;
        }
    }
}