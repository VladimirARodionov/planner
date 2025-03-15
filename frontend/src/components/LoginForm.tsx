import React from 'react';
import { useTranslation } from 'react-i18next';
import {
    Box,
    Button,
    Typography,
    Paper
} from '@mui/material';
import { TelegramIcon } from './icons/TelegramIcon';
import { LanguageSwitcher } from './LanguageSwitcher';

interface LoginFormProps {
    telegramBotName?: string;
    onLoginSuccess?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ telegramBotName, onLoginSuccess }) => {
    const { t } = useTranslation();

    const handleTelegramLogin = () => {
        // Обращаемся к нашему API для инициирования процесса авторизации через Telegram
        // API самостоятельно сформирует правильный URL и перенаправит пользователя
        const callbackUrl = encodeURIComponent(`${window.location.origin}/auth/callback`);
        const apiUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:5000/api'}/auth/telegram/login?redirect_url=${callbackUrl}`;
        
        // Перенаправляем пользователя на API, который обработает авторизацию
        window.location.href = apiUrl;
    };

    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                bgcolor: '#f5f5f5'
            }}
        >
            {/* Переключатель языка в верхнем правом углу */}
            <Box 
                sx={{ 
                    position: 'absolute', 
                    top: 16, 
                    right: 16 
                }}
            >
                <LanguageSwitcher />
            </Box>
            
            <Paper
                elevation={3}
                sx={{
                    p: 4,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    maxWidth: 500,
                    width: '90%'
                }}
            >
                <Typography 
                    variant="h4" 
                    component="h1" 
                    gutterBottom 
                    align="center"
                    sx={{ 
                        fontWeight: 'bold',
                        mb: 2,
                        color: 'primary.main'
                    }}
                >
                    {t('login.welcome')}
                </Typography>
                
                <Typography 
                    variant="body1" 
                    align="center" 
                    sx={{ mb: 4 }}
                >
                    {t('login.please_login')}
                </Typography>
                
                <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    startIcon={<TelegramIcon />}
                    onClick={handleTelegramLogin}
                    sx={{
                        bgcolor: '#0088cc',
                        '&:hover': {
                            bgcolor: '#006699'
                        },
                        py: 1.5,
                        px: 3,
                        borderRadius: 2
                    }}
                >
                    {t('login.login_with_telegram')}
                </Button>
            </Paper>
        </Box>
    );
};

export default LoginForm; 