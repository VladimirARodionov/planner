import React from 'react';
import { useTranslation } from 'react-i18next';
import { Task, DurationType } from '../types/task';
import { TasksAPI } from '../api/tasks';
import { Box, Typography, Chip, IconButton, Card, CardContent, CardActions } from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';

interface TaskItemProps {
    task: Task;
    onTaskUpdated: () => void;
    onEditTask?: (task: Task) => void;
    onDeleteTask?: (taskId: number) => void;
}

const TaskItem: React.FC<TaskItemProps> = ({ task, onTaskUpdated, onEditTask, onDeleteTask }) => {
    const { t } = useTranslation();
    
    const handleDelete = async () => {
        if (window.confirm(t('tasks.delete_confirmation', { title: task.title }))) {
            try {
                await TasksAPI.deleteTask(task.id);
                
                // Вызываем сначала onTaskUpdated, если он передан
                if (onTaskUpdated) {
                    onTaskUpdated();
                }
                
                // И только потом генерируем глобальное событие
                console.log('Dispatching refresh-tasks event after delete');
                window.dispatchEvent(new Event('refresh-tasks'));
            } catch (error) {
                console.error('Error deleting task:', error);
                alert(t('tasks.delete_error'));
            }
        }
    };

    const handleEdit = () => {
        if (onEditTask) {
            onEditTask(task);
        }
    };

    const formatDate = (dateString: string) => {
        // Проверяем, в ISO формате ли строка (содержит T и, возможно, символ Z)
        if (dateString.includes('T')) {
            return new Date(dateString).toLocaleDateString(t('locale_code'), {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        }
        return dateString;
    };
    
    const formatDateTime = (dateString: string) => {
        // Проверяем, в ISO формате ли строка (содержит T и, возможно, символ Z)
        if (dateString.includes('T')) {
            return new Date(dateString).toLocaleDateString(t('locale_code'), {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        return dateString;
    };

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
        <Card sx={{ mb: 2 }}>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography 
                        variant="h6" 
                        component="div"
                        sx={{ 
                            mr: 2,
                            flex: '1 1 auto'
                        }}
                    >
                        {task.title}
                    </Typography>
                    <Box sx={{ 
                        display: 'flex', 
                        gap: 1,
                        flexWrap: 'wrap',
                        justifyContent: 'flex-end',
                        flex: '0 1 auto',
                        maxWidth: { xs: '100%', sm: '60%' },
                        mt: { xs: 1, sm: 0 }
                    }}>
                        {task.status && (
                            <Chip
                                label={task.status.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.status.color || '#ccc',
                                    color: '#fff',
                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)',
                                    textShadow: '0px 0px 2px rgba(0, 0, 0, 0.7)',
                                    maxWidth: '100%',
                                    height: 'auto',
                                    '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        display: 'block',
                                        py: 0.5
                                    }
                                }}
                            />
                        )}
                        {task.priority && (
                            <Chip
                                label={task.priority.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.priority.color || '#ccc',
                                    color: '#fff',
                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)',
                                    textShadow: '0px 0px 2px rgba(0, 0, 0, 0.7)',
                                    maxWidth: '100%',
                                    height: 'auto',
                                    '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        display: 'block',
                                        py: 0.5
                                    }
                                }}
                            />
                        )}
                        {task.type && (
                            <Chip
                                label={task.type.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.type.color || '#ccc',
                                    color: '#fff',
                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)',
                                    textShadow: '0px 0px 2px rgba(0, 0, 0, 0.7)',
                                    maxWidth: '100%',
                                    height: 'auto',
                                    '& .MuiChip-label': {
                                        whiteSpace: 'normal',
                                        display: 'block',
                                        py: 0.5
                                    }
                                }}
                            />
                        )}
                    </Box>
                </Box>

                {task.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {task.description}
                    </Typography>
                )}

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                    {task.deadline && (
                        <Typography variant="body2" color={task.is_overdue ? "error" : "text.secondary"}>
                            {t('tasks.deadline')}: {formatDateTime(task.deadline)}
                            {task.is_overdue && ` (${t('tasks.overdue')})`}
                        </Typography>
                    )}
                    
                    {task.duration && (
                        <Typography variant="body2" color="text.secondary">
                            {t('tasks.duration')}: {task.duration.name} ({task.duration.value} {getDurationTypeLabel(task.duration.type || task.duration.duration_type || '')})
                        </Typography>
                    )}
                    
                    <Typography variant="body2" color="text.secondary">
                        {t('tasks.created')}: {formatDate(task.created_at)}
                    </Typography>
                    
                    {task.completed_at && (
                        <Typography variant="body2" color="text.secondary">
                            {t('tasks.completed')}: {formatDate(task.completed_at)}
                        </Typography>
                    )}
                </Box>
            </CardContent>
            
            <CardActions sx={{ justifyContent: 'flex-end' }}>
                <IconButton 
                    size="small" 
                    color="primary" 
                    onClick={handleEdit}
                    title={t('common.edit')}
                >
                    <EditIcon />
                </IconButton>
                <IconButton 
                    size="small" 
                    color="error" 
                    onClick={handleDelete}
                    title={t('common.delete')}
                >
                    <DeleteIcon />
                </IconButton>
            </CardActions>
        </Card>
    );
};

export default TaskItem; 