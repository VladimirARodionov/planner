import React, { useEffect } from 'react';
import { Box, Container, Typography, Paper, Divider } from '@mui/material';
import { TaskTypeSettings } from '../components/TaskTypeSettings';
import { StatusSettings } from '../components/StatusSettings';
import { PrioritySettings } from '../components/PrioritySettings';
import { DurationSettings } from '../components/DurationSettings';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { TimezoneSwitcher } from '../components/TimezoneSwitcher';
import { TasksAPI } from '../api/tasks';
import { DurationType } from '../types/task';
import { useTranslation } from 'react-i18next';

export const SettingsPage: React.FC = () => {
    const { t } = useTranslation();
    
    // Добавляем отладочную функцию для проверки настроек продолжительностей
    useEffect(() => {
        const checkDurations = async () => {
            try {
                const settings = await TasksAPI.getSettings();
                console.log('Durations from API:', settings.durations);
                
                // Проверка типов данных продолжительностей
                if (settings.durations && settings.durations.length > 0) {
                    // Преобразуем duration_type в type, если нужно
                    settings.durations = settings.durations.map(duration => {
                        if (!duration.type && duration.duration_type) {
                            return {
                                ...duration,
                                type: duration.duration_type as unknown as DurationType
                            };
                        }
                        return duration;
                    });
                    
                    settings.durations.forEach((duration, index) => {
                        console.log(`Duration ${index + 1}:`, {
                            id: duration.id,
                            name: duration.name,
                            type: duration.type || duration.duration_type,
                            value: duration.value,
                            is_active: duration.is_active,
                            is_default: duration.is_default
                        });
                    });
                }
            } catch (error) {
                console.error('Error checking durations:', error);
            }
        };
        
        checkDurations();
    }, []);
    
    return (
        <Container maxWidth="md">
            <Box py={4}>
                <Typography variant="h4" gutterBottom>
                    {t('settings.general')}
                </Typography>
                
                <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
                    <Typography variant="h6" gutterBottom>
                        {t('settings.language')}
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                        <LanguageSwitcher />
                    </Box>
                    
                    <Divider sx={{ my: 2 }} />
                    
                    <Typography variant="h6" gutterBottom>
                        {t('timezone.select')}
                    </Typography>
                    <Box>
                        <TimezoneSwitcher />
                    </Box>
                </Paper>
                
                <Typography variant="h4" gutterBottom sx={{ mt: 4 }}>
                    {t('settings.customization')}
                </Typography>
                
                <Box mb={4}>
                    <TaskTypeSettings />
                </Box>
                
                <Box mb={4}>
                    <StatusSettings />
                </Box>
                
                <Box mb={4}>
                    <PrioritySettings />
                </Box>
                
                <Box mb={4}>
                    <DurationSettings />
                </Box>
            </Box>
        </Container>
    );
}; 