import React, { useEffect, useState } from 'react';
import { Task, Status, Priority, Duration, TaskType } from '../types/task';
import { TasksAPI, CreateTaskDto, UpdateTaskDto } from '../api/tasks';
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
    SelectChangeEvent
} from '@mui/material';

interface TaskFormProps {
    open: boolean;
    onClose: () => void;
    task?: Task;
    onSubmit: (task: CreateTaskDto | UpdateTaskDto) => void;
}

type FormData = {
    title: string;
    description: string;
    type_id: string;
    status_id: number | '';
    priority_id: number | '';
    duration_id: number | '';
};

export const TaskForm: React.FC<TaskFormProps> = ({
    open,
    onClose,
    task,
    onSubmit
}) => {
    const [formData, setFormData] = useState<FormData>({
        title: '',
        description: '',
        type_id: '',
        status_id: '',
        priority_id: '',
        duration_id: ''
    });
    const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
    const [statuses, setStatuses] = useState<Status[]>([]);
    const [priorities, setPriorities] = useState<Priority[]>([]);
    const [durations, setDurations] = useState<Duration[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            loadSettings();
            if (task) {
                console.log('Task for edit:', task);
                
                // Проверяем, что объекты существуют и имеют id
                const typeId = task.type && task.type.id ? task.type.id.toString() : '';
                const statusId = task.status && task.status.id ? task.status.id : '';
                const priorityId = task.priority && task.priority.id ? task.priority.id : '';
                const durationId = task.duration && task.duration.id ? task.duration.id : '';
                
                setFormData({
                    title: task.title,
                    description: task.description || '',
                    type_id: typeId,
                    status_id: statusId,
                    priority_id: priorityId,
                    duration_id: durationId
                });
                
                console.log('Form data after set:', {
                    title: task.title,
                    description: task.description || '',
                    type_id: typeId,
                    status_id: statusId,
                    priority_id: priorityId,
                    duration_id: durationId
                });
            } else {
                setFormData({
                    title: '',
                    description: '',
                    type_id: '',
                    status_id: '',
                    priority_id: '',
                    duration_id: ''
                });
            }
        }
    }, [open, task]);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const [types, settings] = await Promise.all([
                TasksAPI.getTaskTypes(),
                TasksAPI.getSettings()
            ]);
            setTaskTypes(types);
            setStatuses(settings.statuses);
            setPriorities(settings.priorities);
            setDurations(settings.durations);
            setError(null);
        } catch (err) {
            setError('Ошибка при загрузке настроек');
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

    const handleSelectChange = (
        event: SelectChangeEvent<number | ''>,
        field: 'status_id' | 'priority_id' | 'duration_id'
    ) => {
        setFormData({
            ...formData,
            [field]: event.target.value
        });
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
            duration_id: formData.duration_id !== '' ? Number(formData.duration_id) : undefined
        };
        
        console.log('Submitting task data:', submitData);
        onSubmit(submitData);
    };

    if (loading) {
        return <Typography>Загрузка...</Typography>;
    }

    if (error) {
        return <Typography color="error">{error}</Typography>;
    }

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>
                {task ? 'Редактировать задачу' : 'Создать задачу'}
            </DialogTitle>
            <form onSubmit={handleSubmit}>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2}>
                        <TextField
                            label="Название"
                            value={formData.title}
                            onChange={(e) => handleTextChange(e, 'title')}
                            required
                            fullWidth
                        />
                        <TextField
                            label="Описание"
                            value={formData.description}
                            onChange={(e) => handleTextChange(e, 'description')}
                            multiline
                            rows={4}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>Тип задачи</InputLabel>
                            <Select
                                value={formData.type_id}
                                onChange={(e) => setFormData({ ...formData, type_id: e.target.value })}
                                label="Тип задачи"
                            >
                                <MenuItem value="">Не выбран</MenuItem>
                                {taskTypes.map((type) => (
                                    <MenuItem key={type.id} value={type.id.toString()}>
                                        {type.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <FormControl fullWidth>
                            <InputLabel>Статус</InputLabel>
                            <Select
                                value={formData.status_id}
                                onChange={(e) => handleSelectChange(e, 'status_id')}
                                label="Статус"
                            >
                                <MenuItem value="">Не выбран</MenuItem>
                                {statuses.map((status) => (
                                    <MenuItem
                                        key={status.id}
                                        value={status.id}
                                        sx={{
                                            backgroundColor: status.color || '#ccc',
                                            color: '#fff',
                                            '&:hover': {
                                                backgroundColor: status.color || '#ccc',
                                                opacity: 0.8
                                            }
                                        }}
                                    >
                                        {status.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <FormControl fullWidth>
                            <InputLabel>Приоритет</InputLabel>
                            <Select
                                value={formData.priority_id}
                                onChange={(e) => handleSelectChange(e, 'priority_id')}
                                label="Приоритет"
                            >
                                <MenuItem value="">Не выбран</MenuItem>
                                {priorities.map((priority) => (
                                    <MenuItem
                                        key={priority.id}
                                        value={priority.id}
                                        sx={{
                                            backgroundColor: priority.color || '#ccc',
                                            color: '#fff',
                                            '&:hover': {
                                                backgroundColor: priority.color || '#ccc',
                                                opacity: 0.8
                                            }
                                        }}
                                    >
                                        {priority.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <FormControl fullWidth>
                            <InputLabel>Длительность</InputLabel>
                            <Select
                                value={formData.duration_id}
                                onChange={(e) => handleSelectChange(e, 'duration_id')}
                                label="Длительность"
                            >
                                <MenuItem value="">Не выбран</MenuItem>
                                {durations.map((duration) => (
                                    <MenuItem key={duration.id} value={duration.id}>
                                        {duration.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={onClose}>Отмена</Button>
                    <Button type="submit" variant="contained" color="primary">
                        {task ? 'Сохранить' : 'Создать'}
                    </Button>
                </DialogActions>
            </form>
        </Dialog>
    );
}; 