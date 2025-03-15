import React from 'react';
import { useTranslation } from 'react-i18next';
import { Duration, DurationType } from '../types/task';
import { Box, Typography, List, ListItem, ListItemText } from '@mui/material';

interface DurationListProps {
    durations: Duration[];
}

export const DurationList: React.FC<DurationListProps> = ({ durations }) => {
    const { t } = useTranslation();
    
    // Функция для получения человекочитаемого названия типа длительности
    const getDurationTypeLabel = (type: DurationType | string): string => {
        switch (type) {
            case DurationType.DAYS:
            case "DAYS":
            case "days":
                return t('duration_types.days');
            case DurationType.WEEKS:
            case "WEEKS":
            case "weeks":
                return t('duration_types.weeks');
            case DurationType.MONTHS:
            case "MONTHS":
            case "months":
                return t('duration_types.months');
            case DurationType.YEARS:
            case "YEARS":
            case "years":
                return t('duration_types.years');
            default:
                return String(type);
        }
    };

    return (
        <Box>
            <Typography variant="h6" gutterBottom>
                {t('settings.durations')}
            </Typography>
            <List>
                {durations.map((duration) => (
                    <ListItem key={duration.id} divider>
                        <ListItemText
                            primary={duration.name}
                            secondary={`${duration.value} ${getDurationTypeLabel(duration.type || duration.duration_type || '')}`}
                        />
                    </ListItem>
                ))}
            </List>
        </Box>
    );
}; 