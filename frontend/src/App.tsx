import React, { useState, useEffect } from 'react';
import { TaskList } from './components/TaskList';
import { TaskForm } from './components/TaskForm';
import { LoginForm } from './components/LoginForm';
import { Task } from './types/task';
import { TasksAPI, CreateTaskDto, UpdateTaskDto } from './api/tasks';
import {
    AppBar,
    Box,
    Container,
    IconButton,
    Toolbar,
    Typography,
    Snackbar,
    Alert,
    AlertProps,
    Button
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';

export const App: React.FC = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [selectedTask, setSelectedTask] = useState<Task | undefined>();
    const [notification, setNotification] = useState<{
        message: string;
        type: AlertProps['severity'];
    } | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            setIsAuthenticated(true);
        }
    }, []);

    const handleLoginSuccess = (token: string) => {
        setIsAuthenticated(true);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setIsAuthenticated(false);
    };

    const handleCreateTask = () => {
        setSelectedTask(undefined);
        setIsFormOpen(true);
    };

    const handleEditTask = (task: Task) => {
        setSelectedTask(task);
        setIsFormOpen(true);
    };

    const handleCloseForm = () => {
        setIsFormOpen(false);
        setSelectedTask(undefined);
    };

    const handleSubmitTask = async (taskData: CreateTaskDto | UpdateTaskDto) => {
        try {
            if (selectedTask) {
                await TasksAPI.updateTask(selectedTask.id, taskData as UpdateTaskDto);
                setNotification({
                    message: 'Задача успешно обновлена',
                    type: 'success'
                });
            } else {
                await TasksAPI.createTask(taskData as CreateTaskDto);
                setNotification({
                    message: 'Задача успешно создана',
                    type: 'success'
                });
            }
            handleCloseForm();
        } catch (err) {
            setNotification({
                message: 'Произошла ошибка при сохранении задачи',
                type: 'error'
            });
            console.error(err);
        }
    };

    const handleDeleteTask = async (taskId: number) => {
        try {
            await TasksAPI.deleteTask(taskId);
            setNotification({
                message: 'Задача успешно удалена',
                type: 'success'
            });
        } catch (err) {
            setNotification({
                message: 'Произошла ошибка при удалении задачи',
                type: 'error'
            });
            console.error(err);
        }
    };

    const handleCloseNotification = () => {
        setNotification(null);
    };

    if (!isAuthenticated) {
        return <LoginForm onLoginSuccess={handleLoginSuccess} />;
    }

    return (
        <Box sx={{ flexGrow: 1 }}>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                        Планировщик задач
                    </Typography>
                    <IconButton
                        color="inherit"
                        aria-label="create task"
                        onClick={handleCreateTask}
                        sx={{ mr: 2 }}
                    >
                        <AddIcon />
                    </IconButton>
                    <Button color="inherit" onClick={handleLogout}>
                        Выйти
                    </Button>
                </Toolbar>
            </AppBar>

            <Container sx={{ mt: 3 }}>
                <TaskList
                    onEditTask={handleEditTask}
                    onDeleteTask={handleDeleteTask}
                />
            </Container>

            <TaskForm
                open={isFormOpen}
                onClose={handleCloseForm}
                task={selectedTask}
                onSubmit={handleSubmitTask}
            />

            <Snackbar
                open={!!notification}
                autoHideDuration={6000}
                onClose={handleCloseNotification}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Box>
                    {notification && (
                        <Alert
                            onClose={handleCloseNotification}
                            severity={notification.type}
                            sx={{ width: '100%' }}
                        >
                            {notification.message}
                        </Alert>
                    )}
                </Box>
            </Snackbar>
        </Box>
    );
}; 