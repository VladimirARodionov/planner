import React, { useState, useEffect } from 'react';
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
    Typography,
    Switch,
    FormControlLabel,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';

export const DurationSettings: React.FC = () => {
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

    useEffect(() => {
        loadDurations();
    }, []);

    const loadDurations = async () => {
        try {
            const settings = await TasksAPI.getSettings();
            setDurations(settings.durations);
        } catch (error) {
            console.error('Error loading durations:', error);
        }
    };

    const handleOpen = (duration?: Duration) => {
        if (duration) {
            setEditingDuration(duration);
            setFormData({
                name: duration.name,
                type: duration.type,
                value: duration.value,
                is_default: duration.is_default,
                is_active: duration.is_active,
            });
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
            if (editingDuration) {
                await TasksAPI.updateDuration(editingDuration.id, formData);
            } else {
                await TasksAPI.createDuration(formData);
            }
            handleClose();
            loadDurations();
        } catch (error) {
            console.error('Error saving duration:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm('Вы уверены, что хотите удалить эту длительность?')) {
            try {
                await TasksAPI.deleteDuration(id);
                loadDurations();
            } catch (error) {
                console.error('Error deleting duration:', error);
            }
        }
    };

    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Длительности</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpen()}
                >
                    Добавить длительность
                </Button>
            </Box>

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
                            secondary={`${duration.value} ${duration.type}`}
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
                    {editingDuration ? 'Редактировать длительность' : 'Новая длительность'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} mt={2}>
                        <TextField
                            label="Название"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>Тип</InputLabel>
                            <Select
                                value={formData.type}
                                onChange={(e) => setFormData({ ...formData, type: e.target.value as DurationType })}
                                label="Тип"
                            >
                                {Object.values(DurationType).map((type) => (
                                    <MenuItem key={type} value={type}>
                                        {type}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <TextField
                            label="Значение"
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
                            label="По умолчанию"
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.is_active}
                                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                />
                            }
                            label="Активен"
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose}>Отмена</Button>
                    <Button onClick={handleSubmit} variant="contained" color="primary">
                        {editingDuration ? 'Сохранить' : 'Создать'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}; 