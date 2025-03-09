import React, { useState, useEffect } from 'react';
import { Priority } from '../types/task';
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
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';

export const PrioritySettings: React.FC = () => {
    const [priorities, setPriorities] = useState<Priority[]>([]);
    const [open, setOpen] = useState(false);
    const [editingPriority, setEditingPriority] = useState<Priority | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        color: '#808080',
        order: 0,
        is_default: false,
        is_active: true,
    });

    useEffect(() => {
        loadPriorities();
    }, []);

    const loadPriorities = async () => {
        try {
            const settings = await TasksAPI.getSettings();
            setPriorities(settings.priorities);
        } catch (error) {
            console.error('Error loading priorities:', error);
        }
    };

    const handleOpen = (priority?: Priority) => {
        if (priority) {
            setEditingPriority(priority);
            setFormData({
                name: priority.name,
                color: priority.color,
                order: priority.order,
                is_default: priority.is_default,
                is_active: priority.is_active,
            });
        } else {
            setEditingPriority(null);
            setFormData({
                name: '',
                color: '#808080',
                order: 0,
                is_default: false,
                is_active: true,
            });
        }
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
        setEditingPriority(null);
    };

    const handleSubmit = async () => {
        try {
            if (editingPriority) {
                await TasksAPI.updatePriority(editingPriority.id, formData);
            } else {
                await TasksAPI.createPriority(formData);
            }
            handleClose();
            loadPriorities();
        } catch (error) {
            console.error('Error saving priority:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm('Вы уверены, что хотите удалить этот приоритет?')) {
            try {
                await TasksAPI.deletePriority(id);
                loadPriorities();
            } catch (error) {
                console.error('Error deleting priority:', error);
            }
        }
    };

    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Приоритеты</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpen()}
                >
                    Добавить приоритет
                </Button>
            </Box>

            <List>
                {priorities.map((priority) => (
                    <ListItem
                        key={priority.id}
                        sx={{
                            border: '1px solid #ddd',
                            borderRadius: 1,
                            mb: 1,
                            backgroundColor: priority.color + '20',
                        }}
                    >
                        <ListItemText
                            primary={priority.name}
                            sx={{
                                '& .MuiListItemText-primary': {
                                    color: priority.color,
                                    fontWeight: 'bold',
                                },
                            }}
                        />
                        <ListItemSecondaryAction>
                            <IconButton
                                edge="end"
                                aria-label="edit"
                                onClick={() => handleOpen(priority)}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={() => handleDelete(priority.id)}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingPriority ? 'Редактировать приоритет' : 'Новый приоритет'}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} mt={2}>
                        <TextField
                            label="Название"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Цвет"
                            type="color"
                            value={formData.color}
                            onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Порядок"
                            type="number"
                            value={formData.order}
                            onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })}
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
                        {editingPriority ? 'Сохранить' : 'Создать'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}; 