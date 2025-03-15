import React from 'react';
import { useTranslation } from 'react-i18next';
import {
    Box,
    Button,
    Typography,
    Paper,
} from '@mui/material';
import { TelegramIcon } from './icons/TelegramIcon';

interface LoginFormProps {
    telegramBotName?: string;
    onLoginSuccess?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ telegramBotName, onLoginSuccess }) => {
    const { t } = useTranslation();

    const handleTelegramLogin = () => {
        const botName = telegramBotName || 'viewstorebot';
        const callbackUrl = encodeURIComponent(`${window.location.origin}/auth/callback`);
        window.location.href = `https://oauth.telegram.org/auth?bot_id=${botName}&origin=${callbackUrl}&return_to=${callbackUrl}`;
    };

    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                bgcolor: '#f5f5f5'
            }}
        >
            <Paper
                elevation={3}
                sx={{
                    p: 4,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    maxWidth: 400,
                    width: '100%'
                }}
            >
                <Typography variant="h5" component="h1" gutterBottom>
                    {t('login.welcome')}
                </Typography>
                <Typography variant="body1" align="center" sx={{ mb: 3 }}>
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
                        }
                    }}
                >
                    {t('login.login_with_telegram')}
                </Button>
            </Paper>
        </Box>
    );
};

export default LoginForm; 