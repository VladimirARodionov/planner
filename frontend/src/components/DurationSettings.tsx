import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Duration, DurationType } from '../types/task';
import { TasksAPI } from '../api/tasks';
import {
    Box,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Card,
    CardHeader,
    Divider,
    Switch,
    FormControlLabel
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';

export const DurationSettings: React.FC = () => {
    const { t } = useTranslation();
    const [durations, setDurations] = useState<Duration[]>([]);
    const [open, setOpen] = useState(false);
    const [editingDuration, setEditingDuration] = useState<Duration | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        type: DurationType.DAYS,
        value: 1,
        is_default: false,
        is_active: true,
    });

    // Функция для получения человекочитаемого названия типа длительности
    const getDurationTypeLabel = (type: DurationType | string): string => {
        switch (type) {
            case DurationType.DAYS:
            case "DAYS":
            case "days":
                return t('duration_types.days');
            case DurationType.WEEKS:
            case "WEEKS":
            case "weeks":
                return t('duration_types.weeks');
            case DurationType.MONTHS:
            case "MONTHS":
            case "months":
                return t('duration_types.months');
            case DurationType.YEARS:
            case "YEARS":
            case "years":
                return t('duration_types.years');
            default:
                return String(type);
        }
    };

    useEffect(() => {
        loadDurations();
    }, []);

    useEffect(() => {
        if (durations.length > 0) {
            console.log('DurationSettings - loaded durations:', durations);
            durations.forEach((duration, index) => {
                console.log(`Duration ${index + 1}:`, {
                    id: duration.id,
                    name: duration.name,
                    type: duration.type,
                    duration_type: duration.duration_type,
                    value: duration.value
                });
            });
        }
    }, [durations]);

    const loadDurations = async () => {
        try {
            const settings = await TasksAPI.getSettings();
            console.log('Loaded durations in DurationSettings:', settings.durations);
            setDurations(settings.durations);
        } catch (error) {
            console.error('Error loading durations:', error);
        }
    };

    const handleOpen = (duration?: Duration) => {
        if (duration) {
            console.log('Opening for edit duration:', duration);
            console.log('DurationType enum values:', Object.values(DurationType));
            
            // Определяем тип напрямую из строкового значения
            let durationType: DurationType = DurationType.DAYS; // По умолчанию дни
            
            // Получаем строковое значение типа (из type или duration_type)
            const typeValue = duration.type || duration.duration_type;
            console.log('Type value from API:', typeValue);
            
            // Проверяем каждое возможное значение DurationType и ищем соответствие
            // Используем строковое сравнение для предотвращения проблем с типами
            const typeValueStr = String(typeValue).toLowerCase();
            
            if (typeValueStr === 'days') {
                durationType = DurationType.DAYS;
            } else if (typeValueStr === 'weeks') {
                durationType = DurationType.WEEKS;
            } else if (typeValueStr === 'months') {
                durationType = DurationType.MONTHS;
            } else if (typeValueStr === 'years') {
                durationType = DurationType.YEARS;
            }
            
            console.log('Selected durationType:', durationType);
            
            const newFormData = {
                name: duration.name,
                type: durationType,
                value: duration.value,
                is_default: duration.is_default,
                is_active: duration.is_active,
            };
            
            console.log('New form data:', newFormData);
            
            setEditingDuration(duration);
            setFormData(newFormData);
        } else {
            setEditingDuration(null);
            setFormData({
                name: '',
                type: DurationType.DAYS,
                value: 1,
                is_default: false,
                is_active: true,
            });
        }
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
        setEditingDuration(null);
    };

    const handleSubmit = async () => {
        try {
            // Логируем данные перед отправкой на сервер
            console.log('Form data before submit:', formData);
            console.log('Type value from formData:', formData.type);
            
            // Убедимся, что тип отправляется в правильном формате
            const submittingData = {
                ...formData,
                // При необходимости преобразуем тип в строковое значение
                // type: formData.type
            };
            
            console.log('Data to submit:', submittingData);
            
            if (editingDuration) {
                await TasksAPI.updateDuration(editingDuration.id, submittingData);
            } else {
                await TasksAPI.createDuration(submittingData);
            }
            handleClose();
            loadDurations();
        } catch (error) {
            console.error('Error saving duration:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm(t('settings.delete_confirmation'))) {
            try {
                await TasksAPI.deleteDuration(id);
                loadDurations();
            } catch (error) {
                console.error('Error deleting duration:', error);
            }
        }
    };

    return (
        <Card variant="outlined">
            <CardHeader 
                title={t('settings.durations')}
                action={
                    <Button 
                        startIcon={<AddIcon />} 
                        onClick={() => handleOpen()}
                        color="primary"
                    >
                        {t('settings.add_duration')}
                    </Button>
                }
            />
            <Divider />
            <List>
                {durations.map((duration) => (
                    <ListItem
                        key={duration.id}
                        sx={{
                            border: '1px solid #ddd',
                            borderRadius: 1,
                            mb: 1,
                        }}
                    >
                        <ListItemText
                            primary={duration.name}
                            secondary={`${duration.value} ${getDurationTypeLabel(duration.type || duration.duration_type || '')}`}
                        />
                        <ListItemSecondaryAction>
                            <IconButton
                                edge="end"
                                aria-label="edit"
                                onClick={() => handleOpen(duration)}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={() => handleDelete(duration.id)}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingDuration ? t('settings.edit_duration') : t('settings.add_duration')}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} mt={2}>
                        <TextField
                            label={t('settings.name')}
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>{t('tasks.type')}</InputLabel>
                            <Select
                                value={formData.type}
                                onChange={(e) => {
                                    console.log('Selected type:', e.target.value);
                                    setFormData({ ...formData, type: e.target.value as DurationType });
                                }}
                                label={t('tasks.type')}
                            >
                                <MenuItem key={DurationType.DAYS} value={DurationType.DAYS}>
                                    {getDurationTypeLabel(DurationType.DAYS)} ({DurationType.DAYS})
                                </MenuItem>
                                <MenuItem key={DurationType.WEEKS} value={DurationType.WEEKS}>
                                    {getDurationTypeLabel(DurationType.WEEKS)} ({DurationType.WEEKS})
                                </MenuItem>
                                <MenuItem key={DurationType.MONTHS} value={DurationType.MONTHS}>
                                    {getDurationTypeLabel(DurationType.MONTHS)} ({DurationType.MONTHS})
                                </MenuItem>
                                <MenuItem key={DurationType.YEARS} value={DurationType.YEARS}>
                                    {getDurationTypeLabel(DurationType.YEARS)} ({DurationType.YEARS})
                                </MenuItem>
                            </Select>
                        </FormControl>
                        <TextField
                            label={t('settings.value')}
                            type="number"
                            value={formData.value}
                            onChange={(e) => setFormData({ ...formData, value: parseInt(e.target.value) })}
                            fullWidth
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.is_default}
                                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                                />
                            }
                            label={t('common.default')}
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.is_active}
                                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                />
                            }
                            label={t('common.active')}
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose}>{t('common.cancel')}</Button>
                    <Button onClick={handleSubmit} variant="contained" color="primary">
                        {editingDuration ? t('common.save') : t('common.create')}
                    </Button>
                </DialogActions>
            </Dialog>
        </Card>
    );
}; 