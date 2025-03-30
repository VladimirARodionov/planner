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

// Интерфейс для ответа с данными о языке пользователя
export interface UserLanguageResponse {
    language: string;
}

// Интерфейс для ответа с данными о часовом поясе пользователя
export interface UserTimezoneResponse {
    timezone: string;
}

// Интерфейс для часового пояса
export interface Timezone {
    value: string;
    label: string;
    group: string;
}

export const AuthAPI = {
    login: async (username: string, password: string): Promise<LoginResponse> => {
        const response = await api.post<LoginResponse>('/auth/login/', { username, password });
        return response.data;
    },
    
    // Метод для обновления токена доступа
    refreshToken: async (): Promise<boolean> => {
        const refreshToken = localStorage.getItem('refreshToken');
        
        if (!refreshToken) {
            console.error('No refresh token available');
            return false;
        }
        
        try {
            console.log('Attempting to refresh token with refresh token');
            
            const response = await api.post('/auth/refresh/', {
                refresh_token: refreshToken
            });
            
            if (response.data.access_token) {
                localStorage.setItem('token', response.data.access_token);
                
                // Если сервер вернул новый refresh token, сохраняем его
                if (response.data.refresh_token) {
                    localStorage.setItem('refreshToken', response.data.refresh_token);
                }
                
                console.log('Token successfully refreshed');
                return true;
            } else {
                console.error('Refresh response missing access token');
                return false;
            }
        } catch (error) {
            console.error('Error refreshing token:', error);
            return false;
        }
    },
    
    // Метод для получения URL для авторизации через Telegram
    getTelegramAuthUrl: (): string => {
        const currentUrl = window.location.origin;
        return `${API_URL}/auth/telegram/login?redirect_url=${encodeURIComponent(currentUrl + '/auth/callback')}`;
    },
    
    // Метод для получения языка пользователя
    getUserLanguage: async (): Promise<string> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                return navigator.language.split('-')[0]; // Если нет токена, используем язык браузера
            }
            
            const response = await api.get<UserLanguageResponse>('/user/language', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return response.data.language || 'ru';
        } catch (error) {
            console.error('Error fetching user language:', error);
            return 'ru'; // По умолчанию русский
        }
    },
    
    // Метод для установки языка пользователя
    setUserLanguage: async (language: string): Promise<boolean> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                return false; // Если нет токена, не можем сохранить язык
            }
            
            await api.post('/user/language', { language }, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return true;
        } catch (error) {
            console.error('Error setting user language:', error);
            return false;
        }
    },

    // Метод для получения часового пояса пользователя
    getUserTimezone: async (): Promise<string> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Moscow'; // Если нет токена, используем часовой пояс браузера
            }
            
            const response = await api.get<UserTimezoneResponse>('/user/timezone', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return response.data.timezone || 'Europe/Moscow';
        } catch (error) {
            console.error('Error fetching user timezone:', error);
            return 'Europe/Moscow'; // По умолчанию Москва
        }
    },
    
    // Метод для установки часового пояса пользователя
    setUserTimezone: async (timezone: string): Promise<boolean> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                return false; // Если нет токена, не можем сохранить часовой пояс
            }
            
            await api.post('/user/timezone', { timezone }, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return true;
        } catch (error) {
            console.error('Error setting user timezone:', error);
            return false;
        }
    },

    // Метод для получения списка доступных часовых поясов
    getTimezones: async (): Promise<Timezone[]> => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                return []; // Если нет токена, возвращаем пустой список
            }
            
            const response = await api.get<Timezone[]>('/timezones', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            return response.data || [];
        } catch (error) {
            console.error('Error fetching timezones:', error);
            return []; // По умолчанию пустой список
        }
    }
}; 