import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { TaskList } from './components/TaskList';
import { TaskForm } from './components/TaskForm';
import LoginForm from './components/LoginForm';
import { Sidebar } from './components/Sidebar';
import { SettingsPage } from './pages/SettingsPage';
import { AboutPage } from './pages/AboutPage';
import TelegramCallback from './components/TelegramCallback';
import { Task } from './types/task';
import { TasksAPI, CreateTaskDto, UpdateTaskDto } from './api/tasks';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from './components/LanguageSwitcher';
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
    Button,
    useMediaQuery,
    useTheme
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { loadUserLanguage } from './i18n';

// Компонент для защищенных маршрутов
const ProtectedRoute: React.FC<{ element: React.ReactNode }> = ({ element }) => {
    const isAuthenticated = localStorage.getItem('token') !== null;
    return isAuthenticated ? <>{element}</> : <Navigate to="/login" />;
};

// Компонент макета для авторизованного пользователя
const AppLayout: React.FC = () => {
    const { t } = useTranslation();
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
    const [isMenuOpen, setIsMenuOpen] = useState(!isMobile);
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [selectedTask, setSelectedTask] = useState<Task | undefined>();
    const [notification, setNotification] = useState<{
        message: string;
        type: AlertProps['severity'];
    } | null>(null);

    // Загружаем язык пользователя при инициализации
    useEffect(() => {
        loadUserLanguage();
    }, []);

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
            
            // Генерируем событие для обновления списка задач
            window.dispatchEvent(new Event('refresh-tasks'));
        } catch (err) {
            setNotification({
                message: 'Произошла ошибка при сохранении задачи',
                type: 'error'
            });
            console.error(err);
        }
    };

    const handleToggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const handleCloseNotification = () => {
        setNotification(null);
    };

    // Рассчитываем смещение контента при открытом меню
    const contentMargin = isMenuOpen ? '240px' : 0;

    // Обработка пользовательских событий
    useEffect(() => {
        // Обработчик события редактирования задачи
        const handleEditTaskEvent = (event: CustomEvent<Task>) => {
            if (event.detail) {
                setSelectedTask(event.detail);
                setIsFormOpen(true);
            }
        };

        // Добавляем слушатели событий
        window.addEventListener('edit-task', handleEditTaskEvent as EventListener);

        // Отписываемся при размонтировании
        return () => {
            window.removeEventListener('edit-task', handleEditTaskEvent as EventListener);
        };
    }, []);

    // Добавляем useEffect для адаптации меню к размеру экрана
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 600) {
                setIsMenuOpen(false);
            } else {
                setIsMenuOpen(true);
            }
        };

        // Вызываем один раз при монтировании
        handleResize();

        // Слушаем изменение размера окна
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    return (
        <Box sx={{ display: 'flex' }}>
            <AppBar 
                position="fixed" 
                sx={{ 
                    zIndex: (theme) => theme.zIndex.drawer + 1,
                    transition: theme.transitions.create(['width', 'margin'], {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    }),
                    ...(isMenuOpen && {
                        marginLeft: contentMargin,
                        width: `calc(100% - ${contentMargin})`,
                        transition: theme.transitions.create(['width', 'margin'], {
                            easing: theme.transitions.easing.sharp,
                            duration: theme.transitions.duration.enteringScreen,
                        }),
                    })
                }}
            >
                <Toolbar>
                    <Sidebar 
                        open={isMenuOpen} 
                        onClose={handleToggleMenu} 
                        onOpen={handleToggleMenu} 
                    />
                    <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                        {t('common.app_name')}
                    </Typography>
                    <IconButton
                        color="inherit"
                        aria-label="create task"
                        onClick={handleCreateTask}
                        sx={{ mr: 2 }}
                        title={t('tasks.new_task')}
                    >
                        <AddIcon />
                    </IconButton>
                    <LanguageSwitcher />
                    <Button color="inherit" onClick={handleLogout}>
                        {t('common.logout')}
                    </Button>
                </Toolbar>
            </AppBar>

            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    pt: 10,
                    pl: 2,
                    pr: 2,
                    ml: isMenuOpen ? contentMargin : 0,
                    transition: theme.transitions.create('margin', {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    })
                }}
            >
                <Outlet />
            </Box>

            <TaskForm
                open={isFormOpen}
                onClose={handleCloseForm}
                task={selectedTask}
                onSubmit={handleSubmitTask}
                isEditing={!!selectedTask}
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
    useEffect(() => {
        document.title = process.env.REACT_APP_TITLE || 'Планировщик задач';
    }, []);

    return (
        <Router>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/auth/callback" element={<TelegramCallback />} />
                <Route path="/" element={<ProtectedRoute element={<AppLayout />} />}>
                    <Route index element={
                        <Container>
                            <TaskList
                                onEditTask={(task) => {
                                    // Показываем форму редактирования задачи
                                    const event = new CustomEvent('edit-task', { detail: task });
                                    window.dispatchEvent(event);
                                }}
                                refreshTrigger={0}
                            />
                        </Container>
                    } />
                    <Route path="settings" element={<SettingsPage />} />
                    <Route path="about" element={<AboutPage />} />
                </Route>
            </Routes>
        </Router>
    );
}; 