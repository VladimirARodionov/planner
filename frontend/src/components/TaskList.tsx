import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { TasksAPI, PaginationParams, TaskFilters, PaginatedResponse, SettingsAPI, UserPreferences } from '../api/tasks';
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
    onEditTask: (task: Task) => void;
    onDeleteTask?: (taskId: number) => void;
    refreshTrigger: number;
}

export const TaskList: React.FC<TaskListProps> = ({ onEditTask, onDeleteTask, refreshTrigger }): JSX.Element => {
    const { t, i18n } = useTranslation();
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
    const [showCompleted, setShowCompleted] = useState<boolean>(false);
    
    // Состояние для сортировки
    const [sortField, setSortField] = useState<string>('deadline'); // Сортировка по дедлайну по умолчанию
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">('asc'); // По возрастанию по умолчанию
    
    // Флаги для отслеживания состояния
    const isInitialMount = useRef(true);
    const preferencesLoaded = useRef(false);
    const userTriggeredUpdate = useRef(false);
    
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
    
    // Загрузка настроек пользователя
    const loadUserPreferences = useCallback(async () => {
        try {
            console.log('Loading user preferences...');
            const preferences = await SettingsAPI.getUserPreferences();
            console.log('Loaded user preferences:', preferences);

            // Проверяем, что у нас есть предпочтения и они не пустые
            if (preferences && typeof preferences === 'object') {
                // Применяем сохраненные фильтры, если они есть
                if (preferences.filters && Object.keys(preferences.filters).length > 0) {
                    console.log('Applying filters from preferences:', preferences.filters);
                    
                    // Устанавливаем фильтры в состояние компонента
                    setFilters(prevFilters => ({...prevFilters, ...preferences.filters}));
                    
                    // Устанавливаем состояния UI компонентов фильтров
                    if (preferences.filters.status_id !== undefined) {
                        console.log('Setting status filter:', preferences.filters.status_id);
                        setSelectedStatus(Number(preferences.filters.status_id));
                    }
                    
                    if (preferences.filters.priority_id !== undefined) {
                        console.log('Setting priority filter:', preferences.filters.priority_id);
                        setSelectedPriority(Number(preferences.filters.priority_id));
                    }
                    
                    if (preferences.filters.type_id !== undefined) {
                        console.log('Setting type filter:', preferences.filters.type_id);
                        setSelectedType(Number(preferences.filters.type_id));
                    }
                    
                    if (preferences.filters.deadline_from) {
                        console.log('Setting deadline_from filter:', preferences.filters.deadline_from);
                        setDeadlineFrom(new Date(preferences.filters.deadline_from));
                    }
                    
                    if (preferences.filters.deadline_to) {
                        console.log('Setting deadline_to filter:', preferences.filters.deadline_to);
                        setDeadlineTo(new Date(preferences.filters.deadline_to));
                    }
                    
                    if (preferences.filters.is_completed !== undefined) {
                        console.log('Setting is_completed filter:', preferences.filters.is_completed);
                        setShowCompleted(preferences.filters.is_completed);
                    } else {
                        console.log('No is_completed filter found in preferences');
                        setShowCompleted(true);
                    }
                } else {
                    console.log('No filters found in preferences or filters is empty:', preferences.filters);
                }
                
                // Применяем сохраненную сортировку, если она есть
                if (preferences.sort_by) {
                    console.log('Setting sort_by:', preferences.sort_by);
                    setSortField(preferences.sort_by);
                }
                
                if (preferences.sort_order) {
                    console.log('Setting sort_order:', preferences.sort_order);
                    setSortDirection(preferences.sort_order);
                }
            } else {
                console.log('No valid preferences received');
            }
            
            preferencesLoaded.current = true;
        } catch (error) {
            console.error('Error loading user preferences:', error);
            preferencesLoaded.current = true;
        }
    }, []);
    
    // Сохранение настроек пользователя
    const saveUserPreferences = useCallback(async () => {
        // Предотвращаем сохранение во время начальной загрузки
        if (isInitialMount.current || !preferencesLoaded.current) {
            console.log('Skipping save during initial mount or before preferences loaded');
            return;
        }
        
        try {
            console.log('Saving user preferences...');
            const preferences: UserPreferences = {
                filters: filters,
                sort_by: sortField,
                sort_order: sortDirection
            };
            
            console.log('Saving user preferences:', preferences);
            await SettingsAPI.saveUserPreferences(preferences);
            console.log('User preferences saved successfully');
        } catch (error) {
            console.error('Error saving user preferences:', error);
        }
    }, [filters, sortField, sortDirection]);

    // Функция загрузки задач с текущими параметрами
    const fetchTasksStable = useCallback(async () => {
        try {
            console.log('Fetching tasks with current state...');
            setLoading(true);
            
            // Создаем объект параметров пагинации с текущими значениями
            const paginationParams = {
                ...pagination,
                search: searchQuery,
                sort_by: sortField,
                sort_order: sortDirection
            };
            
            console.log('Pagination params:', paginationParams);
            console.log('Filters:', filters);
            
            const data = await TasksAPI.getTasksPaginated(paginationParams, filters);
            setTaskData(data);
            setError(null);
        } catch (err) {
            console.error('Error fetching tasks:', err);
            setError(t('tasks.error_loading'));
        } finally {
            setLoading(false);
        }
    }, [pagination, searchQuery, sortField, sortDirection, filters, t]);
    
    // Эффект для начальной инициализации
    useEffect(() => {
        console.log('TaskList mounted - initializing...');
        isInitialMount.current = true;
        preferencesLoaded.current = false;
        
        // Загружаем настройки и справочники
        fetchSettings();
        
        // Загружаем пользовательские настройки
        loadUserPreferences();
        
        // Создаем стабильный обработчик событий
        const handleRefreshEvent = () => {
            console.log('Refresh event called - updating tasks');
            fetchTasksStable();
        };
        
        // Подписываемся на событие
        window.addEventListener('refresh-tasks', handleRefreshEvent);
        
        // Очистка при размонтировании
        return () => {
            console.log('TaskList unmounted - cleaning up');
            window.removeEventListener('refresh-tasks', handleRefreshEvent);
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    
    // Эффект для загрузки задач после загрузки предпочтений
    useEffect(() => {
        // Загружаем задачи только когда предпочтения загружены
        if (preferencesLoaded.current) {
            console.log('Preferences loaded - fetching tasks');
            fetchTasksStable();
            isInitialMount.current = false;
        }
    }, [preferencesLoaded.current]); // eslint-disable-line react-hooks/exhaustive-deps
    
    // Эффект для реагирования на изменения пагинации, refreshTrigger
    useEffect(() => {
        if (!isInitialMount.current && preferencesLoaded.current) {
            console.log('Pagination changed - fetching tasks');
            fetchTasksStable();
        }
    }, [pagination.page, refreshTrigger]); // eslint-disable-line react-hooks/exhaustive-deps
    
    // Эффект для реагирования на изменения фильтров и сортировки
    useEffect(() => {
        if (!isInitialMount.current && preferencesLoaded.current && userTriggeredUpdate.current) {
            console.log('Filters or sort changed by user - fetching tasks and saving preferences');
            fetchTasksStable();
            saveUserPreferences();
            userTriggeredUpdate.current = false;
        }
    }, [filters, sortField, sortDirection]); // eslint-disable-line react-hooks/exhaustive-deps

    const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
        setPagination(prev => ({ ...prev, page: value }));
    };

    const handleSearch = () => {
        setPagination(prev => ({ ...prev, page: 1 }));
        // Установка флага пользовательского обновления
        userTriggeredUpdate.current = true;
        // Обновление фильтров, чтобы включить поисковый запрос
        applyFilters();
    };

    const handleClearFilters = async () => {
        // Установка флага пользовательского обновления
        userTriggeredUpdate.current = true;
        
        setFilters({is_completed: false});
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
        // Установка флага пользовательского обновления
        userTriggeredUpdate.current = true;
        
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
        // Установка флага пользовательского обновления
        userTriggeredUpdate.current = true;
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

        if (sortField) {
            var sortFieldText;
            switch (sortField) {
                case "title" : sortFieldText = t('tasks.sort.by_title'); break;
                case "deadline": sortFieldText = t('tasks.sort.by_deadline'); break;
                case "priority": sortFieldText = t('tasks.sort.by_priority'); break;
                case "status": sortFieldText =t('tasks.sort.by_status'); break;
                case "created_at": sortFieldText = t('tasks.sort.by_created_date'); break;
            }
            activeFilters.push(`Сортировка: ${sortFieldText} (${sortDirection === 'asc' ? t('tasks.sort.ascending') : t('tasks.sort.descending')})`);
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
                    {t('tasks.task_list')}
                </Typography>
                
                {/* Поиск */}
                <Grid container spacing={2} mb={2}>
                    <Grid item xs={12} sm={6} md={4}>
                        <TextField
                            fullWidth
                            label={t('common.search')}
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
                            {t('common.find')}
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
                            <Typography>{t('common.filters')}</Typography>
                        </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Grid container spacing={2}>
                            {/* Фильтр по статусу */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="status-filter-label">{t('tasks.status')}</InputLabel>
                                    <Select
                                        labelId="status-filter-label"
                                        id="status-filter"
                                        value={selectedStatus}
                                        label={t('tasks.status')}
                                        onChange={(e) => setSelectedStatus(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>{t('tasks.all_statuses')}</em>
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
                                    <InputLabel id="priority-filter-label">{t('tasks.priority')}</InputLabel>
                                    <Select
                                        labelId="priority-filter-label"
                                        id="priority-filter"
                                        value={selectedPriority}
                                        label={t('tasks.priority')}
                                        onChange={(e) => setSelectedPriority(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>{t('tasks.all_priorities')}</em>
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
                                    <InputLabel id="type-filter-label">{t('tasks.type')}</InputLabel>
                                    <Select
                                        labelId="type-filter-label"
                                        id="type-filter"
                                        value={selectedType}
                                        label={t('tasks.type')}
                                        onChange={(e) => setSelectedType(e.target.value as number)}
                                    >
                                        <MenuItem value="">
                                            <em>{t('tasks.all_types')}</em>
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
                                    label={t('common.show_completed')}
                                />
                            </Grid>
                            
                            {/* Фильтр по дедлайну */}
                            <Grid item xs={12} sm={6} md={3}>
                                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={i18n.language === 'ru' ? ru : undefined}>
                                    <DatePicker
                                        label={t('tasks.deadline_from')}
                                        value={deadlineFrom}
                                        onChange={(date: Date | null) => setDeadlineFrom(date)}
                                        slotProps={{ textField: { fullWidth: true } }}
                                    />
                                </LocalizationProvider>
                            </Grid>
                            
                            <Grid item xs={12} sm={6} md={3}>
                                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={i18n.language === 'ru' ? ru : undefined}>
                                    <DatePicker
                                        label={t('tasks.deadline_to')}
                                        value={deadlineTo}
                                        onChange={(date: Date | null) => setDeadlineTo(date)}
                                        slotProps={{ textField: { fullWidth: true } }}
                                    />
                                </LocalizationProvider>
                            </Grid>
                            
                            {/* Сортировка */}
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth>
                                    <InputLabel id="sort-field-label">{t('tasks.sort.sort_by')}</InputLabel>
                                    <Select
                                        labelId="sort-field-label"
                                        id="sort-field"
                                        value={sortField}
                                        label={t('tasks.sort.sort_by')}
                                        onChange={(e) => setSortField(e.target.value)}
                                    >
                                        <MenuItem value="">
                                            <em>{t('tasks.sort.no_sort')}</em>
                                        </MenuItem>
                                        <MenuItem value="title">{t('tasks.sort.by_title')}</MenuItem>
                                        <MenuItem value="deadline">{t('tasks.sort.by_deadline')}</MenuItem>
                                        <MenuItem value="priority">{t('tasks.sort.by_priority')}</MenuItem>
                                        <MenuItem value="status">{t('tasks.sort.by_status')}</MenuItem>
                                        <MenuItem value="created_at">{t('tasks.sort.by_created_date')}</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            
                            <Grid item xs={12} sm={6} md={3}>
                                <FormControl fullWidth disabled={!sortField}>
                                    <InputLabel id="sort-direction-label">{t('tasks.sort.direction')}</InputLabel>
                                    <Select
                                        labelId="sort-direction-label"
                                        id="sort-direction"
                                        value={sortDirection}
                                        label={t('tasks.sort.direction')}
                                        onChange={(e) => setSortDirection(e.target.value as 'asc' | 'desc')}
                                    >
                                        <MenuItem value="asc">{t('tasks.sort.ascending')}</MenuItem>
                                        <MenuItem value="desc">{t('tasks.sort.descending')}</MenuItem>
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
                                        {t('common.reset')}
                                    </Button>
                                    <Button 
                                        variant="contained" 
                                        onClick={() => {
                                            // Устанавливаем флаг пользовательской активности
                                            userTriggeredUpdate.current = true;
                                            
                                            // Применяем фильтры
                                            applyFilters();
                                            
                                            // Устанавливаем пагинацию на первую страницу
                                            setPagination(prev => ({
                                                ...prev,
                                                page: 1
                                            }));
                                        }}
                                        startIcon={<FilterListIcon />}
                                    >
                                        {t('common.apply')}
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
                            {t('tasks.active_filters')}:
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
                                onTaskUpdated={fetchTasksStable}
                                onEditTask={onEditTask}
                                onDeleteTask={onDeleteTask}
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
                <Typography align="center">{t('tasks.no_tasks')}</Typography>
            )}
        </Box>
    );
}; 