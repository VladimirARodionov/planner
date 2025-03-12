import React from 'react';
import {
    Box,
    Button,
    Typography,
    Paper,
} from '@mui/material';
import { AuthAPI } from '../api/auth';

interface LoginFormProps {
    onLoginSuccess: (token: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onLoginSuccess }) => {

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