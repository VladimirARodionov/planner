import React from 'react';
import { Task } from '../types/task';
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
                onTaskUpdated();
            } catch (error) {
                console.error('Error deleting task:', error);
                alert('Не удалось удалить задачу. Пожалуйста, попробуйте позже.');
            }
        }
    };

    const handleEdit = () => {
        console.log('Edit button clicked');
        console.log('onEditTask exists:', !!onEditTask);
        console.log('Task data:', task);
        if (onEditTask) {
            onEditTask(task);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
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
                            Длительность: {task.duration.name} ({task.duration.value} {task.duration.type})
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