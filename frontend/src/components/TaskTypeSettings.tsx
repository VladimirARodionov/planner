import React, { useState, useEffect } from 'react';
import { TaskType } from '../types/task';
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

export const TaskTypeSettings: React.FC = () => {
    const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
    const [open, setOpen] = useState(false);
    const [editingType, setEditingType] = useState<TaskType | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        color: '#808080',
        order: 0,
        is_default: false,
        is_active: true,
    });

    useEffect(() => {
        loadTaskTypes();
    }, []);

    const loadTaskTypes = async () => {
        try {
            const types = await TasksAPI.getTaskTypes();
            setTaskTypes(types);
        } catch (error) {
            console.error('Error loading task types:', error);
        }
    };

    const handleOpen = (type?: TaskType) => {
        if (type) {
            setEditingType(type);
            setFormData({
                name: type.name,
                description: type.description || '',
                color: type.color || '#808080',
                order: type.order || 0,
                is_default: type.is_default || false,
                is_active: type.is_active || true,
            });
        } else {
            setEditingType(null);
            setFormData({
                name: '',
                description: '',
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
        setEditingType(null);
    };

    const handleSubmit = async () => {
        try {
            if (editingType) {
                await TasksAPI.updateTaskType(editingType.id, formData);
            } else {
                await TasksAPI.createTaskType(formData);
            }
            handleClose();
            loadTaskTypes();
        } catch (error) {
            console.error('Error saving task type:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm('Вы уверены, что хотите удалить этот тип задачи?')) {
            try {
                await TasksAPI.deleteTaskType(id);
                loadTaskTypes();
            } catch (error) {
                console.error('Error deleting task type:', error);
            }
        }
    };

    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Типы задач</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpen()}
                >
                    Добавить тип
                </Button>
            </Box>

            <List>
                {taskTypes.map((type) => (
                    <ListItem
                        key={type.id}
                        sx={{
                            border: '1px solid #ddd',
                            borderRadius: 1,
                            mb: 1,
                            backgroundColor: type.color + '20',
                        }}
                    >
                        <ListItemText
                            primary={type.name}
                            secondary={type.description}
                            sx={{
                                '& .MuiListItemText-primary': {
                                    color: type.color,
                                    fontWeight: 'bold',
                                },
                            }}
                        />
                        <ListItemSecondaryAction>
                            <IconButton
                                edge="end"
                                aria-label="edit"
                                onClick={() => handleOpen(type)}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={() => handleDelete(type.id)}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingType ? 'Редактировать тип задачи' : 'Новый тип задачи'}
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
                            label="Описание"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            fullWidth
                            multiline
                            rows={2}
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
                        {editingType ? 'Сохранить' : 'Создать'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}; 