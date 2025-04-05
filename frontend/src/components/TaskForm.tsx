import React, { useEffect, useState } from 'react';
import { Task, Status, Priority, Duration, TaskType, DurationType } from '../types/task';
import { TasksAPI, CreateTaskDto, UpdateTaskDto } from '../api/tasks';
import { AuthAPI } from '../api/auth';
import {
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Typography,
    SelectChangeEvent,
    Grid,
    FormControlLabel,
    Checkbox,
    useMediaQuery,
    Theme,
    CircularProgress
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { ru } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';
import { formatInTimeZone, utcToZonedTime } from 'date-fns-tz';

interface TaskFormProps {
    open: boolean;
    onClose: () => void;
    task?: Task;
    onSubmit: (task: CreateTaskDto | UpdateTaskDto) => void;
    isEditing?: boolean;
}

type FormData = {
    title: string;
    description: string;
    type_id: string;
    status_id: number | '';
    priority_id: number | '';
    duration_id: number | '';
    deadline: Date | null;
    completed: boolean;
    completed_at?: string | null;
};

export const TaskForm: React.FC<TaskFormProps> = ({
    open,
    onClose,
    task,
    onSubmit,
    isEditing = false
}) => {
    const { t, i18n } = useTranslation();
    const isSmallScreen = useMediaQuery((theme: Theme) => theme.breakpoints.down('sm'));
    const [formData, setFormData] = useState<FormData>({
        title: '',
        description: '',
        type_id: '',
        status_id: '',
        priority_id: '',
        duration_id: '',
        deadline: null,
        completed: false
    });
    const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
    const [statuses, setStatuses] = useState<Status[]>([]);
    const [priorities, setPriorities] = useState<Priority[]>([]);
    const [durations, setDurations] = useState<Duration[]>([]);
    const [loading, setLoading] = useState(false);
    const [calculatingDeadline, setCalculatingDeadline] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);
    const [userTimezone, setUserTimezone] = useState<string>('Europe/Moscow');

    useEffect(() => {
        // Загружаем настройки и информацию о пользователе при открытии формы
        if (open) {
            loadSettingsAndUser();
        }
    }, [open]);

    const loadSettingsAndUser = async () => {
        try {
            setLoading(true);
            const [types, settings, timezone] = await Promise.all([
                TasksAPI.getTaskTypes(),
                TasksAPI.getSettings(),
                AuthAPI.getUserTimezone()
            ]);
            setTaskTypes(types);
            setStatuses(settings.statuses);
            setPriorities(settings.priorities);
            setDurations(settings.durations);
            setUserTimezone(timezone || 'Europe/Moscow');
            setError(null);

            // Если есть задача для редактирования, загружаем её данные
            if (task) {
                console.log('Task for edit:', task);
                
                const typeId = task.type && task.type.id ? task.type.id.toString() : '';
                const statusId = task.status && task.status.id ? task.status.id : '';
                const priorityId = task.priority && task.priority.id ? task.priority.id : '';
                const durationId = task.duration && task.duration.id ? task.duration.id : '';
                
                const deadlineDate = task.deadline_iso ? new Date(task.deadline_iso) : (task.deadline ? new Date(task.deadline) : null);
                
                const isCompleted = !!(task.completed || 
                                    task.completed_at || 
                                    (task.status && task.status.is_final));
                
                setFormData({
                    title: task.title,
                    description: task.description || '',
                    type_id: typeId,
                    status_id: statusId,
                    priority_id: priorityId,
                    duration_id: durationId,
                    deadline: deadlineDate,
                    completed: !!isCompleted
                });
                
                setSelectedDate(deadlineDate);
            } else {
                setFormData({
                    title: '',
                    description: '',
                    type_id: '',
                    status_id: '',
                    priority_id: '',
                    duration_id: '',
                    deadline: null,
                    completed: false
                });
                setSelectedDate(null);
            }
        } catch (err) {
            setError('Ошибка при загрузке данных');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleTextChange = (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
        field: 'title' | 'description'
    ) => {
        setFormData({
            ...formData,
            [field]: event.target.value
        });
    };

    const handleSelectChange = async (
        event: SelectChangeEvent<number | string | ''>,
        field: 'status_id' | 'priority_id' | 'duration_id' | 'type_id'
    ) => {
        const newValue = event.target.value;
        
        console.log(`Select changed: ${field} = ${newValue}, type: ${typeof newValue}`);
        
        const updatedFormData = {
            ...formData,
            [field]: newValue
        };
        
        if (field === 'status_id' && newValue !== '') {
            const selectedStatus = statuses.find(status => status.id === Number(newValue));
            if (selectedStatus) {
                updatedFormData.completed = selectedStatus.is_final;
            }
        }
        
        setFormData(updatedFormData);

        if (field === 'duration_id' && newValue !== '') {
            try {
                console.log(`Calculating deadline for duration_id: ${newValue}`);
                setCalculatingDeadline(true);
                
                const durationId = parseInt(String(newValue), 10);
                console.log(`Parsed duration ID for API: ${durationId}`);
                
                const deadline = await TasksAPI.calculateDeadline(durationId);
                console.log(`API response for deadline:`, deadline);
                
                if (deadline) {
                    // Преобразуем дату дедлайна в часовой пояс пользователя
                    const zonedDeadline = utcToZonedTime(deadline, userTimezone);
                    console.log('Deadline in user timezone:', formatInTimeZone(zonedDeadline, userTimezone, 'yyyy-MM-dd HH:mm:ss'));
                    
                    // Получаем текущее время в часовом поясе пользователя
                    const nowInUserTZ = utcToZonedTime(new Date(), userTimezone);
                    
                    // Устанавливаем текущее время для даты дедлайна
                    zonedDeadline.setHours(
                        nowInUserTZ.getHours(),
                        nowInUserTZ.getMinutes(),
                        nowInUserTZ.getSeconds()
                    );
                    console.log('Deadline with current time:', formatInTimeZone(zonedDeadline, userTimezone, 'yyyy-MM-dd HH:mm:ss'));
                    
                    setFormData({
                        ...updatedFormData,
                        deadline: zonedDeadline
                    });
                    
                    setSelectedDate(zonedDeadline);
                } else {
                    console.error('Deadline calculation returned null');
                }
            } catch (err) {
                console.error('Error calculating deadline:', err);
                setError('Ошибка при расчете дедлайна');
            } finally {
                setCalculatingDeadline(false);
            }
        }
    };

    const handleDateChange = (date: Date | null) => {
        console.log('Date picker changed:', date);
        setSelectedDate(date);
        
        if (date) {
            console.log('User timezone from server:', userTimezone);
            
            // Получаем дату в часовом поясе пользователя
            const zonedDate = utcToZonedTime(date, userTimezone);
            console.log('Zoned date:', formatInTimeZone(zonedDate, userTimezone, 'yyyy-MM-dd HH:mm:ss'));
            
            // Получаем текущее время в часовом поясе пользователя
            const nowInUserTZ = utcToZonedTime(new Date(), userTimezone);
            
            // Устанавливаем текущее время для выбранной даты
            zonedDate.setHours(
                nowInUserTZ.getHours(),
                nowInUserTZ.getMinutes(),
                nowInUserTZ.getSeconds()
            );
            console.log('Zoned date with current time:', formatInTimeZone(zonedDate, userTimezone, 'yyyy-MM-dd HH:mm:ss'));
            
            // Сохраняем дату в состоянии формы
            setFormData({ ...formData, deadline: zonedDate });
        } else {
            setFormData({ ...formData, deadline: null });
        }
        
        if (error) {
            setError(null);
        }
    };

    const handleSubmit = (event: React.FormEvent) => {
        event.preventDefault();
        
        // Преобразуем строковые значения в числа, если они не пустые
        const submitData: CreateTaskDto | UpdateTaskDto = {
            title: formData.title,
            description: formData.description || null,
            type_id: formData.type_id ? parseInt(formData.type_id) : undefined,
            status_id: formData.status_id !== '' ? Number(formData.status_id) : undefined,
            priority_id: formData.priority_id !== '' ? Number(formData.priority_id) : undefined,
            duration_id: formData.duration_id !== '' ? Number(formData.duration_id) : undefined,
            deadline: formData.deadline ? formData.deadline.toISOString() : undefined,
            completed: formData.completed
        };
        
        console.log('Submitting task data:', submitData);
        onSubmit(submitData);
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

    if (loading) {
        return <Typography>Загрузка...</Typography>;
    }

    if (error) {
        return <Typography color="error">{error}</Typography>;
    }

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth fullScreen={isSmallScreen}>
            <DialogTitle>
                {isEditing ? t('tasks.edit_task') : t('tasks.new_task')}
            </DialogTitle>
            <form onSubmit={handleSubmit}>
                <DialogContent>
                    <Grid container spacing={2}>
                        <Grid item xs={12}>
                            <TextField
                                autoFocus
                                name="title"
                                label={t('tasks.title')}
                                fullWidth
                                value={formData.title}
                                onChange={(e) => handleTextChange(e, 'title')}
                                error={!!error}
                                helperText={error}
                                margin="normal"
                            />
                        </Grid>
                        
                        <Grid item xs={12}>
                            <TextField
                                name="description"
                                label={t('tasks.description')}
                                fullWidth
                                multiline
                                rows={4}
                                value={formData.description}
                                onChange={(e) => handleTextChange(e, 'description')}
                                margin="normal"
                            />
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth margin="normal">
                                <InputLabel id="status-label">{t('tasks.status')}</InputLabel>
                                <Select
                                    labelId="status-label"
                                    name="status_id"
                                    value={formData.status_id}
                                    label={t('tasks.status')}
                                    onChange={(e) => handleSelectChange(e, 'status_id')}
                                >
                                    <MenuItem 
                                        value="" 
                                        sx={{
                                            '&.Mui-selected': {
                                                backgroundColor: '#f5f5f5',
                                                fontWeight: 'bold'
                                            },
                                            '&.Mui-selected:hover': {
                                                backgroundColor: '#e0e0e0'
                                            }
                                        }}
                                    >
                                        Не выбран
                                    </MenuItem>
                                    {statuses.map((status) => (
                                        <MenuItem
                                            key={status.id}
                                            value={status.id}
                                            sx={{
                                                backgroundColor: status.color || '#ccc',
                                                color: '#fff',
                                                textShadow: '0px 0px 2px rgba(0, 0, 0, 0.7)',
                                                '&:hover': {
                                                    backgroundColor: status.color || '#ccc',
                                                    opacity: 0.9
                                                },
                                                '&.Mui-selected': {
                                                    backgroundColor: status.color || '#ccc',
                                                    border: '2px solid #fff',
                                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)',
                                                    fontWeight: 'bold'
                                                },
                                                '&.Mui-selected:hover': {
                                                    backgroundColor: status.color || '#ccc',
                                                    opacity: 0.9,
                                                    border: '2px solid #fff',
                                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)'
                                                }
                                            }}
                                        >
                                            {status.name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth margin="normal">
                                <InputLabel id="priority-label">{t('tasks.priority')}</InputLabel>
                                <Select
                                    labelId="priority-label"
                                    name="priority_id"
                                    value={formData.priority_id}
                                    label={t('tasks.priority')}
                                    onChange={(e) => handleSelectChange(e, 'priority_id')}
                                >
                                    <MenuItem 
                                        value="" 
                                        sx={{
                                            '&.Mui-selected': {
                                                backgroundColor: '#f5f5f5',
                                                fontWeight: 'bold'
                                            },
                                            '&.Mui-selected:hover': {
                                                backgroundColor: '#e0e0e0'
                                            }
                                        }}
                                    >
                                        Не выбран
                                    </MenuItem>
                                    {priorities.map((priority) => (
                                        <MenuItem
                                            key={priority.id}
                                            value={priority.id}
                                            sx={{
                                                backgroundColor: priority.color || '#ccc',
                                                color: '#fff',
                                                textShadow: '0px 0px 2px rgba(0, 0, 0, 0.7)',
                                                '&:hover': {
                                                    backgroundColor: priority.color || '#ccc',
                                                    opacity: 0.9
                                                },
                                                '&.Mui-selected': {
                                                    backgroundColor: priority.color || '#ccc',
                                                    border: '2px solid #fff',
                                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)',
                                                    fontWeight: 'bold'
                                                },
                                                '&.Mui-selected:hover': {
                                                    backgroundColor: priority.color || '#ccc',
                                                    opacity: 0.9,
                                                    border: '2px solid #fff',
                                                    boxShadow: '0 0 5px rgba(0, 0, 0, 0.5)'
                                                }
                                            }}
                                        >
                                            {priority.name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth margin="normal">
                                <InputLabel id="type-label">{t('tasks.type')}</InputLabel>
                                <Select
                                    labelId="type-label"
                                    name="type_id"
                                    value={formData.type_id}
                                    label={t('tasks.type')}
                                    onChange={(e) => handleSelectChange(e, 'type_id')}
                                >
                                    <MenuItem 
                                        value="" 
                                        sx={{
                                            '&.Mui-selected': {
                                                backgroundColor: '#f5f5f5',
                                                fontWeight: 'bold'
                                            },
                                            '&.Mui-selected:hover': {
                                                backgroundColor: '#e0e0e0'
                                            }
                                        }}
                                    >
                                        Не выбран
                                    </MenuItem>
                                    {taskTypes.map((type) => (
                                        <MenuItem 
                                            key={type.id} 
                                            value={type.id.toString()}
                                            sx={{
                                                backgroundColor: type.color || '#f0f0f0',
                                                '&:hover': {
                                                    backgroundColor: type.color || '#e0e0e0',
                                                    opacity: 0.9
                                                },
                                                '&.Mui-selected': {
                                                    backgroundColor: '#e3f2fd',
                                                    fontWeight: 'bold',
                                                    border: '2px solid #1976d2'
                                                },
                                                '&.Mui-selected:hover': {
                                                    backgroundColor: '#bbdefb',
                                                    opacity: 0.9
                                                }
                                            }}
                                        >
                                            {type.name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <FormControl fullWidth margin="normal">
                                <InputLabel id="duration-label">{t('tasks.duration')}</InputLabel>
                                <Select
                                    labelId="duration-label"
                                    name="duration_id"
                                    value={formData.duration_id || ''}
                                    label={t('tasks.duration')}
                                    onChange={(e) => handleSelectChange(e, 'duration_id')}
                                    endAdornment={calculatingDeadline && <CircularProgress size={20} />}
                                >
                                    <MenuItem value="">{t('tasks.no_duration')}</MenuItem>
                                    {durations.map((duration) => (
                                        <MenuItem 
                                            key={duration.id} 
                                            value={duration.id}
                                            sx={{
                                                '&.Mui-selected': {
                                                    backgroundColor: '#e3f2fd',
                                                    fontWeight: 'bold'
                                                },
                                                '&.Mui-selected:hover': {
                                                    backgroundColor: '#bbdefb'
                                                }
                                            }}
                                        >
                                            {duration.name} ({duration.value} {getDurationTypeLabel(duration.type || duration.duration_type || '')})
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <LocalizationProvider 
                                dateAdapter={AdapterDateFns} 
                                adapterLocale={i18n.language === 'ru' ? ru : undefined}
                            >
                                <DatePicker
                                    label={t('tasks.deadline')}
                                    value={selectedDate}
                                    onChange={handleDateChange}
                                    slotProps={{
                                        textField: {
                                            fullWidth: true,
                                            margin: 'normal',
                                            error: !!error,
                                            helperText: error
                                        }
                                    }}
                                />
                            </LocalizationProvider>
                        </Grid>
                        
                        <Grid item xs={12} sm={6}>
                            <Box sx={{ pt: 2 }}>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            name="completed"
                                            checked={formData.completed}
                                            onChange={(e) => {
                                                const target = e.target as HTMLInputElement;
                                                setFormData({
                                                    ...formData,
                                                    completed: target.checked,
                                                    completed_at: target.checked ? new Date().toISOString() : null
                                                });
                                            }}
                                        />
                                    }
                                    label={t('tasks.completed')}
                                />
                            </Box>
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={onClose}>{t('common.cancel')}</Button>
                    <Button type="submit" variant="contained" color="primary">
                        {isEditing ? t('common.save') : t('common.create')}
                    </Button>
                </DialogActions>
            </form>
        </Dialog>
    );
}; 