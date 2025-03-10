import React, { useState } from 'react';
import {
    Box,
    Button,
    TextField,
    Typography,
    Paper,
    Divider,
} from '@mui/material';
import { AuthAPI } from '../api/auth';

interface LoginFormProps {
    onLoginSuccess: (token: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onLoginSuccess }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const response = await AuthAPI.login(username, password);
            localStorage.setItem('token', response.access);
            localStorage.setItem('refreshToken', response.refresh);
            localStorage.setItem('user', response.user);
            onLoginSuccess(response.access);
        } catch (err) {
            setError('Ошибка авторизации. Проверьте логин и пароль.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleTelegramLogin = () => {
        // Получаем URL для авторизации через Telegram и перенаправляем пользователя
        const telegramAuthUrl = AuthAPI.getTelegramAuthUrl();
        window.location.href = telegramAuthUrl;
    };

    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                bgcolor: 'background.default'
            }}
        >
            <Paper
                elevation={3}
                sx={{
                    p: 4,
                    width: '100%',
                    maxWidth: 400,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 2
                }}
            >
                <Typography variant="h5" component="h1" align="center" gutterBottom>
                    Вход в систему
                </Typography>
                <form onSubmit={handleSubmit}>
                    <Box display="flex" flexDirection="column" gap={2}>
                        <TextField
                            label="Имя пользователя"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            fullWidth
                        />
                        <TextField
                            label="Пароль"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            fullWidth
                        />
                        {error && (
                            <Typography color="error" align="center">
                                {error}
                            </Typography>
                        )}
                        <Button
                            type="submit"
                            variant="contained"
                            color="primary"
                            fullWidth
                            disabled={loading}
                        >
                            {loading ? 'Вход...' : 'Войти'}
                        </Button>
                    </Box>
                </form>
                
                <Divider sx={{ my: 2 }}>или</Divider>
                
                <Button
                    variant="outlined"
                    color="primary"
                    fullWidth
                    onClick={handleTelegramLogin}
                    sx={{
                        bgcolor: '#0088cc',
                        color: 'white',
                        '&:hover': {
                            bgcolor: '#0077b5',
                        }
                    }}
                >
                    Войти через Telegram
                </Button>
            </Paper>
        </Box>
    );
}; 