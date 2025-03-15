import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { Task, Settings, Status, Priority, Duration, TaskType } from '../types/task';
import { AuthAPI } from './auth';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
    baseURL: API_URL,
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
}

export interface UpdateTaskDto {
    title?: string;
    description?: string | null;
    type_id?: number;
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
    deadline?: string;
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

    createPriority: async (priority: {
        name: string;
        color?: string;
        order?: number;
        is_active?: boolean;
        is_default?: boolean;
    }) => {
        const response = await api.post<Priority>('/settings/priority/', priority);
        return response.data;
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

    updatePriority: async (priorityId: number, priority: Partial<Priority>) => {
        const response = await api.put<Priority>(`/settings/priority/${priorityId}`, priority);
        return response.data;
    },

    deletePriority: async (priorityId: number) => {
        await api.delete(`/settings/priority/${priorityId}`);
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
    }
}