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

export const AuthAPI = {
    login: async (username: string, password: string): Promise<LoginResponse> => {
        const response = await api.post<LoginResponse>('/auth/login/', { username, password });
        return response.data;
    },
    
    // Метод для получения URL для авторизации через Telegram
    getTelegramAuthUrl: (): string => {
        const currentUrl = window.location.origin;
        return `${API_URL}/auth/telegram/login?redirect_url=${encodeURIComponent(currentUrl + '/auth/callback')}`;
    }
}; 