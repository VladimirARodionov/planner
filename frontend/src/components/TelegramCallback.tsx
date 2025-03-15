import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

const TelegramCallback: React.FC = () => {
    const { t } = useTranslation();
    const location = useLocation();
    const navigate = useNavigate();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const handleCallback = async () => {
            try {
                console.log('Location:', location);
                console.log('Search params:', location.search);
                
                // Получаем параметры из URL
                const queryParams = new URLSearchParams(location.search);
                
                // Проверяем наличие необходимых параметров
                const accessToken = queryParams.get('access_token');
                const refreshToken = queryParams.get('refresh_token');
                const userId = queryParams.get('user_id');
                
                if (!accessToken || !refreshToken || !userId) {
                    throw new Error(t('login.missing_auth_params'));
                }
                
                console.log('Auth params:', { accessToken, refreshToken, userId });
                
                // Сохраняем токены в localStorage
                localStorage.setItem('token', accessToken);
                localStorage.setItem('refreshToken', refreshToken);
                localStorage.setItem('user', userId);
                
                // Перенаправляем на главную страницу
                navigate('/');
            } catch (err) {
                console.error('Error handling Telegram callback:', err);
                setError(t('login.telegram_auth_error'));
            }
        };

        handleCallback();
    }, [location, navigate, t]);

    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
            }}
        >
            {error ? (
                <Typography color="error" variant="h6">
                    {error}
                </Typography>
            ) : (
                <>
                    <CircularProgress size={60} />
                    <Typography variant="h6" sx={{ mt: 2 }}>
                        {t('login.telegram_login_process')}
                    </Typography>
                </>
            )}
        </Box>
    );
};

export default TelegramCallback; 