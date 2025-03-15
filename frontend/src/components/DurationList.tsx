import React from 'react';
import { Duration, DurationType } from '../types/task';
import { Box, Typography, List, ListItem, ListItemText } from '@mui/material';

interface DurationListProps {
    durations: Duration[];
}

export const DurationList: React.FC<DurationListProps> = ({ durations }) => {
    // Функция для получения человекочитаемого названия типа длительности
    const getDurationTypeLabel = (type: DurationType | string): string => {
        switch (type) {
            case DurationType.DAYS:
            case "DAYS":
            case "days":
                return 'дней';
            case DurationType.WEEKS:
            case "WEEKS":
            case "weeks":
                return 'недель';
            case DurationType.MONTHS:
            case "MONTHS":
            case "months":
                return 'месяцев';
            case DurationType.YEARS:
            case "YEARS":
            case "years":
                return 'лет';
            default:
                return String(type);
        }
    };

    return (
        <Box>
            <Typography variant="h6" gutterBottom>
                Продолжительности
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