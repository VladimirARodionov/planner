import React, { useState, useEffect, useCallback } from 'react';
import { TasksAPI, PaginationParams, TaskFilters, PaginatedResponse } from '../api/tasks';
import { Task } from '../types/task';
import TaskItem from './TaskItem';
import { Box, CircularProgress, Typography, Pagination, TextField, Button, Grid } from '@mui/material';

interface TaskListProps {
    onEditTask?: (task: Task) => void;
    onDeleteTask?: (taskId: number) => void;
    refreshTrigger?: number;
}
export const TaskList: React.FC<TaskListProps> = ({ onEditTask, onDeleteTask, refreshTrigger }) => {
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [taskData, setTaskData] = useState<PaginatedResponse | null>(null);
    const [pagination, setPagination] = useState<PaginationParams>({
        page: 1,
        page_size: 10,
    });
    const [filters, setFilters] = useState<TaskFilters>({});
    const [searchQuery, setSearchQuery] = useState<string>('');

    const fetchTasks = useCallback(async () => {
        try {
            console.log('Fetching tasks...');
            setLoading(true);
            const paginationParams: PaginationParams = {
                ...pagination,
                search: searchQuery
            };
            console.log('Pagination params:', paginationParams);
            console.log('Filters:', filters);
            const data = await TasksAPI.getTasksPaginated(paginationParams, filters);
            console.log('Fetched tasks:', data);
            setTaskData(data);
            setError(null);
        } catch (err) {
            console.error('Error fetching tasks:', err);
            setError('Не удалось загрузить задачи. Пожалуйста, попробуйте позже.');
        } finally {
            setLoading(false);
        }
    }, [pagination, searchQuery, filters]);

    useEffect(() => {
        console.log('TaskList useEffect triggered', { 
            page: pagination.page, 
            sort_by: pagination.sort_by, 
            sort_order: pagination.sort_order, 
            filters,
            refreshTrigger,
            searchQuery 
        });
        fetchTasks();
    }, [pagination.page, pagination.sort_by, pagination.sort_order, filters, refreshTrigger, searchQuery, fetchTasks]);

    const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
        setPagination(prev => ({ ...prev, page: value }));
    };

    const handleSearch = () => {
        setPagination(prev => ({ ...prev, page: 1 }));
        fetchTasks();
    };

    const handleClearFilters = () => {
        setFilters({});
        setSearchQuery('');
        setPagination({
            page: 1,
            page_size: 10
        });
    };

    if (loading && !taskData) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <Typography color="error">{error}</Typography>
            </Box>
        );
    }

    return (
        <Box>
            <Box mb={3}>
                <Typography variant="h5" component="h2" gutterBottom>
                    Список задач
                </Typography>
                
                <Grid container spacing={2} mb={2}>
                    <Grid item xs={12} sm={6} md={4}>
                        <TextField
                            fullWidth
                            label="Поиск"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <Button 
                            fullWidth 
                            variant="contained" 
                            onClick={handleSearch}
                        >
                            Найти
                        </Button>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <Button 
                            fullWidth 
                            variant="outlined" 
                            onClick={handleClearFilters}
                        >
                            Сбросить фильтры
                        </Button>
                    </Grid>
                </Grid>
            </Box>

            {taskData && taskData.tasks.length > 0 ? (
                <>
                    <Box mb={2}>
                        {taskData.tasks.map((task) => (
                            <TaskItem 
                                key={task.id} 
                                task={task} 
                                onTaskUpdated={fetchTasks}
                                onEditTask={onEditTask}
                            />
                        ))}
                    </Box>
                    
                    <Box display="flex" justifyContent="center" mt={3}>
                        <Pagination
                            count={taskData.pagination.total_pages}
                            page={pagination.page}
                            onChange={handlePageChange}
                            color="primary"
                        />
                    </Box>
                </>
            ) : (
                <Typography align="center">Задачи не найдены</Typography>
            )}
        </Box>
    );
};

export default TaskList; 