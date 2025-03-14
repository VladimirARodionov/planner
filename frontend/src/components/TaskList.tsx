import React, { useState, useEffect, useCallback } from 'react';
import { TasksAPI, PaginationParams, TaskFilters, PaginatedResponse } from '../api/tasks';
import { Task, Status, Priority, TaskType } from '../types/task';
import TaskItem from './TaskItem';
import { 
    Box, 
    CircularProgress, 
    Typography, 
    Pagination, 
    TextField, 
    Button, 
    Grid, 
    FormControl, 
    InputLabel, 
    Select, 
    MenuItem, 
    Accordion, 
    AccordionSummary, 
    AccordionDetails,
    Chip,
    FormControlLabel,
    Checkbox,
    Stack
} from '@mui/material';
import { 
    FilterList as FilterListIcon, 
    ExpandMore as ExpandMoreIcon, 
    Clear as ClearIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { ru } from 'date-fns/locale';

interface TaskListProps {
    onEditTask?: (task: Task) => void;
    onDeleteTask?: (taskId: number) => void;
    refreshTrigger?: number;
}

export const TaskList: React.FC<TaskListProps> = ({ onEditTask, refreshTrigger }) => {
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [taskData, setTaskData] = useState<PaginatedResponse | null>(null);
    const [pagination, setPagination] = useState<PaginationParams>({
        page: 1,
        page_size: 10,
    });
    const [filters, setFilters] = useState<TaskFilters>({});
    const [searchQuery, setSearchQuery] = useState<string>('');
    
    // Состояния для фильтров
    const [statuses, setStatuses] = useState<Status[]>([]);
    const [priorities, setPriorities] = useState<Priority[]>([]);
    const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
    const [selectedStatus, setSelectedStatus] = useState<number | ''>('');
    const [selectedPriority, setSelectedPriority] = useState<number | ''>('');
    const [selectedType, setSelectedType] = useState<number | ''>('');
    const [deadlineFrom, setDeadlineFrom] = useState<Date | null>(null);
    const [deadlineTo, setDeadlineTo] = useState<Date | null>(null);
    const [showCompleted, setShowCompleted] = useState<boolean>(true);
    
    // Состояние для сортировки
    const [sortField, setSortField] = useState<string | ''>('');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    
    // Загрузка настроек (статусы, приоритеты, типы задач)
    const fetchSettings = useCallback(async () => {
        try {
            const settings = await TasksAPI.getSettings();
            setStatuses(settings.statuses);
            setPriorities(settings.priorities);
            
            const types = await TasksAPI.getTaskTypes();
            setTaskTypes(types);
        } catch (err) {
            console.error('Error fetching settings:', err);
        }
    }, []);
    
    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const fetchTasks = useCallback(async () => {
        try {
            console.log('Fetching tasks...');
            setLoading(true);
            const paginationParams: PaginationParams = {
                ...pagination,
                search: searchQuery
            };
            
            // Добавляем параметры сортировки
            if (sortField) {
                paginationParams.sort_by = sortField;
                paginationParams.sort_order = sortDirection;
            }
            
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
    }, [pagination, searchQuery, filters, sortField, sortDirection]);

    useEffect(() => {
        fetchTasks();
    }, [pagination.page, filters, refreshTrigger, fetchTasks]);

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
        setSelectedStatus('');
        setSelectedPriority('');
        setSelectedType('');
        setDeadlineFrom(null);
        setDeadlineTo(null);
        setShowCompleted(true);
        setSortField('');
        setSortDirection('asc');
        setPagination({
            page: 1,
            page_size: 10
        });
    };
    
    const applyFilters = () => {
        const newFilters: TaskFilters = {};
        
        if (selectedStatus !== '') {
            newFilters.status_id = selectedStatus as number;
        }
        
        if (selectedPriority !== '') {
            newFilters.priority_id = selectedPriority as number;
        }
        
        if (selectedType !== '') {
            newFilters.type_id = selectedType as number;
        }
        
        if (deadlineFrom) {
            newFilters.deadline_from = deadlineFrom.toISOString().split('T')[0];
        }
        
        if (deadlineTo) {
            newFilters.deadline_to = deadlineTo.toISOString().split('T')[0];
        }
        
        // Если не показываем завершенные задачи, устанавливаем is_completed = false
        if (!showCompleted) {
            newFilters.is_completed = false;
        }
        
        setFilters(newFilters);
        setPagination(prev => ({ ...prev, page: 1 }));
    };
    
    const applySorting = () => {
        if (sortField) {
            setPagination(prev => ({
                ...prev,
                page: 1,
                sort_by: sortField,
                sort_order: sortDirection
            }));
        } else {
            setPagination(prev => ({
                ...prev,
                page: 1,
                sort_by: undefined,
                sort_order: 'asc'
            }));
        }
    };
    
    // Получаем активные фильтры для отображения
    const getActiveFilters = () => {
        const activeFilters = [];
        
        if (selectedStatus !== '') {
            const status = statuses.find(s => s.id === selectedStatus);
            if (status) {
                activeFilters.push(`Статус: ${status.name}`);
            }
        }
        
        if (selectedPriority !== '') {
            const priority = priorities.find(p => p.id === selectedPriority);
            if (priority) {
                activeFilters.push(`Приоритет: ${priority.name}`);
            }
        }
        
        if (selectedType !== '') {
            const type = taskTypes.find(t => t.id === selectedType);
            if (type) {
                activeFilters.push(`Тип: ${type.name}`);
            }
        }
        
        if (deadlineFrom) {
            activeFilters.push(`Дедлайн от: ${deadlineFrom.toLocaleDateString()}`);
        }
        
        if (deadlineTo) {
            activeFilters.push(`Дедлайн до: ${deadlineTo.toLocaleDateString()}`);
        }
        
        if (!showCompleted) {
            activeFilters.push('Только незавершенные');
        }
        
        if (searchQuery) {
            activeFilters.push(`Поиск: "${searchQuery}"`);
        }
        
        return activeFilters;
    };
    
    const activeFilters = getActiveFilters();

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
                
                {/* Поиск */}
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
                </Grid>
                
                {/* Аккордеон с фильтрами */}
                <Accordion>
                    <AccordionSummary
                        expandIcon={<ExpandMoreIcon />}
                        aria-controls="filter-content"
                        id="filter-header"
                    >
                        <Box display="flex" alignItems="center">
                            <FilterListIcon sx={{ mr: 1 }} />
                            <Typography>Фильтры</Typography>
                        </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Grid container spacing={2}>
                            {/* Фильтр по статусу */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="status-filter-label">Статус</InputLabel>
                                    <Select
                                        labelId="status-filter-label"
                                        id="status-filter"
                                        value={selectedStatus}
                                        label="Статус"
                                        onChange={(e) => setSelectedStatus(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>Все статусы</em>
                                        </MenuItem>
                                        {statuses.map((status) => (
                                            <MenuItem key={status.id} value={status.id}>
                                                <Box display="flex" alignItems="center">
                                                    <Box 
                                                        width={16} 
                                                        height={16} 
                                                        bgcolor={status.color} 
                                                        borderRadius="50%" 
                                                        mr={1} 
                                                    />
                                                    {status.name}
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            {/* Фильтр по приоритету */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="priority-filter-label">Приоритет</InputLabel>
                                    <Select
                                        labelId="priority-filter-label"
                                        id="priority-filter"
                                        value={selectedPriority}
                                        label="Приоритет"
                                        onChange={(e) => setSelectedPriority(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>Все приоритеты</em>
                                        </MenuItem>
                                        {priorities.map((priority) => (
                                            <MenuItem key={priority.id} value={priority.id}>
                                                <Box display="flex" alignItems="center">
                                                    <Box 
                                                        width={16} 
                                                        height={16} 
                                                        bgcolor={priority.color} 
                                                        borderRadius="50%" 
                                                        mr={1} 
                                                    />
                                                    {priority.name}
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            {/* Фильтр по типу задачи */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="type-filter-label">Тип задачи</InputLabel>
                                    <Select
                                        labelId="type-filter-label"
                                        id="type-filter"
                                        value={selectedType}
                                        label="Тип задачи"
                                        onChange={(e) => setSelectedType(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>Все типы</em>
                                        </MenuItem>
                                        {taskTypes.map((type) => (
                                            <MenuItem key={type.id} value={type.id}>
                                                <Box display="flex" alignItems="center">
                                                    {type.color && (
                                                        <Box 
                                                            width={16} 
                                                            height={16} 
                                                            bgcolor={type.color} 
                                                            borderRadius="50%" 
                                                            mr={1} 
                                                        />
                                                    )}
                                                    {type.name}
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            {/* Фильтр по завершенным задачам */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={showCompleted}
                                            onChange={(e) => setShowCompleted(e.target.checked)}
                                        />
                                    }
                                    label="Показывать завершенные"
                                />
                            </Grid>
                            
                            {/* Фильтр по дедлайну */}
                            <Grid item xs={12} sm={6} md={3}>
                                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ru}>
                                    <DatePicker
                                        label="Дедлайн от"
                                        value={deadlineFrom}
                                        onChange={(date: Date | null) => setDeadlineFrom(date)}
                                        slotProps={{ textField: { fullWidth: true } }}
                                    />
                                </LocalizationProvider>
                            </Grid>
                            
                            <Grid item xs={12} sm={6} md={3}>
                                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ru}>
                                    <DatePicker
                                        label="Дедлайн до"
                                        value={deadlineTo}
                                        onChange={(date: Date | null) => setDeadlineTo(date)}
                                        slotProps={{ textField: { fullWidth: true } }}
                                    />
                                </LocalizationProvider>
                            </Grid>
                            
                            {/* Сортировка */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="sort-field-label">Сортировка</InputLabel>
                                    <Select
                                        labelId="sort-field-label"
                                        id="sort-field"
                                        value={sortField}
                                        label="Сортировка"
                                        onChange={(e) => setSortField(e.target.value)}
                                    >
                                        <MenuItem value="">
                                            <em>Без сортировки</em>
                                        </MenuItem>
                                        <MenuItem value="title">По названию</MenuItem>
                                        <MenuItem value="deadline">По дедлайну</MenuItem>
                                        <MenuItem value="priority">По приоритету</MenuItem>
                                        <MenuItem value="status">По статусу</MenuItem>
                                        <MenuItem value="created_at">По дате создания</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth disabled={!sortField}>
                                    <InputLabel id="sort-direction-label">Направление</InputLabel>
                                    <Select
                                        labelId="sort-direction-label"
                                        id="sort-direction"
                                        value={sortDirection}
                                        label="Направление"
                                        onChange={(e) => setSortDirection(e.target.value as 'asc' | 'desc')}
                                    >
                                        <MenuItem value="asc">По возрастанию</MenuItem>
                                        <MenuItem value="desc">По убыванию</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            {/* Кнопки применения фильтров и сортировки */}
                            <Grid item xs={12}>
                                <Box display="flex" justifyContent="flex-end" gap={2}>
                                    <Button 
                                        variant="outlined" 
                                        onClick={handleClearFilters}
                                        startIcon={<ClearIcon />}
                                    >
                                        Сбросить все
                                    </Button>
                                    <Button 
                                        variant="contained" 
                                        onClick={() => {
                                            applyFilters();
                                            applySorting();
                                        }}
                                        startIcon={<FilterListIcon />}
                                    >
                                        Применить
                                    </Button>
                                </Box>
                            </Grid>
                        </Grid>
                    </AccordionDetails>
                </Accordion>
                
                {/* Отображение активных фильтров */}
                {activeFilters.length > 0 && (
                    <Box mt={2} mb={2}>
                        <Typography variant="subtitle2" gutterBottom>
                            Активные фильтры:
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {activeFilters.map((filter, index) => (
                                <Chip 
                                    key={index} 
                                    label={filter} 
                                    onDelete={() => handleClearFilters()} 
                                    color="primary" 
                                    variant="outlined"
                                    sx={{ margin: '4px' }}
                                />
                            ))}
                        </Stack>
                    </Box>
                )}
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