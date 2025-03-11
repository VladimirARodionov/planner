import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface LoginResponse {
    user: string;
    access: string;
    refresh: string;
}

export interface RefreshResponse {
    user: string;
    access: string;
}

export const AuthAPI = {
    login: async (username: string, password: string): Promise<LoginResponse> => {
        const response = await api.post<LoginResponse>('/auth/login/', { username, password });
        return response.data;
    },
    
    // Метод для обновления токена доступа
    refreshToken: async (): Promise<RefreshResponse> => {
        const refreshToken = localStorage.getItem('refreshToken');
        if (!refreshToken) {
            throw new Error('Refresh token not found');
        }
        
        const response = await api.post<RefreshResponse>('/auth/refresh/', {}, {
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });
        
        // Обновляем токен в localStorage
        localStorage.setItem('token', response.data.access);
        
        return response.data;
    },
    
    // Метод для получения URL для авторизации через Telegram
    getTelegramAuthUrl: (): string => {
        const currentUrl = window.location.origin;
        return `${API_URL}/auth/telegram/login?redirect_url=${encodeURIComponent(currentUrl + '/auth/callback')}`;
    }
}; 