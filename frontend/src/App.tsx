import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { TaskList } from './components/TaskList';
import { TaskForm } from './components/TaskForm';
import { LoginForm } from './components/LoginForm';
import TelegramCallback from './components/TelegramCallback';
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

// Компонент для защищенных маршрутов
const ProtectedRoute: React.FC<{ element: React.ReactNode }> = ({ element }) => {
    const isAuthenticated = localStorage.getItem('token') !== null;
    return isAuthenticated ? <>{element}</> : <Navigate to="/login" />;
};

// Основной компонент приложения
const MainApp: React.FC = () => {
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [selectedTask, setSelectedTask] = useState<Task | undefined>();
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [notification, setNotification] = useState<{
        message: string;
        type: AlertProps['severity'];
    } | null>(null);

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        window.location.href = '/login';
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
            setRefreshTrigger(prev => prev + 1);
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
            setRefreshTrigger(prev => prev + 1);
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
                    refreshTrigger={refreshTrigger}
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

// Компонент для страницы входа
const LoginPage: React.FC = () => {
    const isAuthenticated = localStorage.getItem('token') !== null;
    
    if (isAuthenticated) {
        return <Navigate to="/" />;
    }
    
    const handleLoginSuccess = () => {
        window.location.href = '/';
    };
    
    return <LoginForm onLoginSuccess={handleLoginSuccess} />;
};

// Главный компонент с маршрутизацией
export const App: React.FC = () => {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/auth/callback" element={<TelegramCallback />} />
                <Route path="/" element={<ProtectedRoute element={<MainApp />} />} />
            </Routes>
        </Router>
    );
}; 