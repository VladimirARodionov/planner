import React from 'react';
import { Task, DurationType } from '../types/task';
import { TasksAPI } from '../api/tasks';
import { Box, Typography, Chip, IconButton, Card, CardContent, CardActions } from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';

interface TaskItemProps {
    task: Task;
    onTaskUpdated: () => void;
    onEditTask?: (task: Task) => void;
 }
const TaskItem: React.FC<TaskItemProps> = ({ task, onTaskUpdated, onEditTask }) => {
    const handleDelete = async () => {
        if (window.confirm(`Вы уверены, что хотите удалить задачу "${task.title}"?`)) {
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
                alert('Не удалось удалить задачу. Пожалуйста, попробуйте позже.');
            }
        }
    };

    const handleEdit = () => {
        console.log('Edit button clicked for task:', task.id);
        
        if (onEditTask) {
            console.log('Using direct callback for editing');
            onEditTask(task);
        } else {
            // Создаем пользовательское событие для редактирования задачи
            console.log('Dispatching edit-task event');
            const event = new CustomEvent('edit-task', { detail: task });
            window.dispatchEvent(event);
        }
    };

    const formatDate = (dateString: string) => {
        // Проверяем, в ISO формате ли строка (содержит T и, возможно, символ Z)
        if (dateString.includes('T')) {
            return new Date(dateString).toLocaleDateString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
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
        <Card sx={{ mb: 2 }}>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6" component="div">
                        {task.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        {task.status && (
                            <Chip
                                label={task.status.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.status.color || '#ccc',
                                    color: '#fff'
                                }}
                            />
                        )}
                        {task.priority && (
                            <Chip
                                label={task.priority.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.priority.color || '#ccc',
                                    color: '#fff'
                                }}
                            />
                        )}
                        {task.type && (
                            <Chip
                                label={task.type.name}
                                size="small"
                                sx={{
                                    backgroundColor: task.type.color || '#ccc',
                                    color: '#fff'
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
                            Срок: {formatDate(task.deadline)}
                            {task.is_overdue && " (просрочено)"}
                        </Typography>
                    )}
                    
                    {task.duration && (
                        <Typography variant="body2" color="text.secondary">
                            Длительность: {task.duration.name} ({task.duration.value} {getDurationTypeLabel(task.duration.type || task.duration.duration_type || '')})
                        </Typography>
                    )}
                    
                    <Typography variant="body2" color="text.secondary">
                        Создано: {formatDate(task.created_at)}
                    </Typography>
                    
                    {task.completed_at && (
                        <Typography variant="body2" color="text.secondary">
                            Завершено: {formatDate(task.completed_at)}
                        </Typography>
                    )}
                </Box>
            </CardContent>
            
            <CardActions sx={{ justifyContent: 'flex-end' }}>
                <IconButton 
                    size="small" 
                    color="primary" 
                    onClick={handleEdit}
                >
                    <EditIcon />
                </IconButton>
                <IconButton size="small" color="error" onClick={handleDelete}>
                    <DeleteIcon />
                </IconButton>
            </CardActions>
        </Card>
    );
};

export default TaskItem; 