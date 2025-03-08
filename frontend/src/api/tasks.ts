import axios from 'axios';
import { Task, Settings, Status, Priority, Duration } from '../types/task';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Добавляем токен к каждому запросу
api.interceptors.request.use((config: any) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export interface CreateTaskDto {
    title: string;
    description?: string | null;
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
}

export interface UpdateTaskDto {
    title?: string;
    description?: string | null;
    status_id?: number;
    priority_id?: number;
    duration_id?: number;
}

export const TasksAPI = {
    // Задачи
    getTasks: async (filters?: {
        status_id?: number;
        priority_id?: number;
        duration_id?: number;
        is_completed?: boolean;
    }) => {
        const response = await api.get<{ tasks: Task[] }>('/tasks/', { params: filters });
        return response.data.tasks;
    },

    createTask: async (task: CreateTaskDto) => {
        const response = await api.post<Task>('/tasks/', task);
        return response.data;
    },

    updateTask: async (taskId: number, task: UpdateTaskDto) => {
        const response = await api.put<Task>(`/tasks/${taskId}`, task);
        return response.data;
    },

    deleteTask: async (taskId: number) => {
        await api.delete(`/tasks/${taskId}`);
    },

    // Настройки
    getSettings: async () => {
        const response = await api.get<Settings>('/settings/');
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

    updatePriority: async (priorityId: number, priority: Partial<Priority>) => {
        const response = await api.put<Priority>(`/settings/priority/${priorityId}`, priority);
        return response.data;
    },

    updateDuration: async (durationId: number, duration: Partial<Duration>) => {
        const response = await api.put<Duration>(`/settings/duration/${durationId}`, duration);
        return response.data;
    },

    deleteStatus: async (statusId: number) => {
        await api.delete(`/settings/status/${statusId}`);
    },

    deletePriority: async (priorityId: number) => {
        await api.delete(`/settings/priority/${priorityId}`);
    },

    deleteDuration: async (durationId: number) => {
        await api.delete(`/settings/duration/${durationId}`);
    },
}; 