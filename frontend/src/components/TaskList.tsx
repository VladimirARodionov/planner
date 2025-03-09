import React, { useEffect, useState } from 'react';
import { Task } from '../types/task';
import { TasksAPI } from '../api/tasks';
import { Box, List, ListItem, ListItemText, Typography, Chip, IconButton } from '@mui/material';
import { Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';

interface TaskListProps {
    onEditTask?: (task: Task) => void;
    onDeleteTask?: (taskId: number) => void;
}

export const TaskList: React.FC<TaskListProps> = ({ onEditTask, onDeleteTask }) => {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadTasks();
    }, []);

    const loadTasks = async () => {
        try {
            setLoading(true);
            const tasks = await TasksAPI.getTasks();
            setTasks(tasks);
            setError(null);
        } catch (err) {
            setError('Ошибка при загрузке задач');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (taskId: number) => {
        try {
            await TasksAPI.deleteTask(taskId);
            setTasks(tasks.filter(task => task.id !== taskId));
            onDeleteTask?.(taskId);
        } catch (err) {
            setError('Ошибка при удалении задачи');
            console.error(err);
        }
    };

    if (loading) {
        return <Typography>Загрузка...</Typography>;
    }

    if (error) {
        return <Typography color="error">{error}</Typography>;
    }

    return (
        <Box>
            <List>
                {tasks.map((task) => (
                    <ListItem
                        key={task.id}
                        secondaryAction={
                            <Box>
                                <IconButton
                                    edge="end"
                                    aria-label="edit"
                                    onClick={() => onEditTask?.(task)}
                                    sx={{ mr: 1 }}
                                >
                                    <EditIcon />
                                </IconButton>
                                <IconButton
                                    edge="end"
                                    aria-label="delete"
                                    onClick={() => handleDelete(task.id)}
                                >
                                    <DeleteIcon />
                                </IconButton>
                            </Box>
                        }
                    >
                        <ListItemText
                            primary={
                                <Box display="flex" alignItems="center" gap={1}>
                                    <Typography>{task.title}</Typography>
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
                                </Box>
                            }
                            secondary={
                                <Box>
                                    <Typography variant="body2" color="text.secondary">
                                        {task.description}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {task.deadline && `Срок: ${new Date(task.deadline).toLocaleDateString()}`}
                                    </Typography>
                                </Box>
                            }
                        />
                    </ListItem>
                ))}
            </List>
        </Box>
    );
}; 