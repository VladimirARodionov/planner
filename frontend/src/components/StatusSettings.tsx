import React, { useState, useEffect } from 'react';
import { Status } from '../types/task';
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

export const StatusSettings: React.FC = () => {
    const [statuses, setStatuses] = useState<Status[]>([]);
    const [open, setOpen] = useState(false);
    const [editingStatus, setEditingStatus] = useState<Status | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        code: '',
        color: '#808080',
        order: 0,
        is_default: false,
        is_active: true,
        is_final: false,
    });

    useEffect(() => {
        loadStatuses();
    }, []);

    const loadStatuses = async () => {
        try {
            const settings = await TasksAPI.getSettings();
            setStatuses(settings.statuses);
        } catch (error) {
            console.error('Error loading statuses:', error);
        }
    };

    const handleOpen = (status?: Status) => {
        if (status) {
            setEditingStatus(status);
            setFormData({
                name: status.name,
                code: status.code,
                color: status.color,
                order: status.order,
                is_default: status.is_default,
                is_active: status.is_active,
                is_final: status.is_final,
            });
        } else {
            setEditingStatus(null);
            setFormData({
                name: '',
                code: '',
                color: '#808080',
                order: 0,
                is_default: false,
                is_active: true,
                is_final: false,
            });
        }
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
        setEditingStatus(null);
    };

    const handleSubmit = async () => {
        try {
            if (editingStatus) {
                await TasksAPI.updateStatus(editingStatus.id, formData);
            } else {
                await TasksAPI.createStatus(formData);
            }
            handleClose();
            loadStatuses();
        } catch (error) {
            console.error('Error saving status:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm('Вы уверены, что хотите удалить этот статус?')) {
            try {
                await TasksAPI.deleteStatus(id);
                loadStatuses();
            } catch (error) {
                console.error('Error deleting status:', error);
            }
        }
    };

    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Статусы</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpen()}
                >
                    Добавить статус
                </Button>
            </Box>

            <List>
                {statuses.map((status) => (
                    <ListItem
                        key={status.id}
                        sx={{
                            border: '1px solid #ddd',
                            borderRadius: 1,
                            mb: 1,
                            backgroundColor: status.color + '20',
                        }}
                    >
                        <ListItemText
                            primary={status.name}
                            secondary={`Код: ${status.code}`}
                            sx={{
                                '& .MuiListItemText-primary': {
                                    color: status.color,
                                    fontWeight: 'bold',
                                },
                            }}
                        />
                        <ListItemSecondaryAction>
                            <IconButton
                                edge="end"
                                aria-label="edit"
                                onClick={() => handleOpen(status)}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={() => handleDelete(status.id)}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingStatus ? 'Редактировать статус' : 'Новый статус'}
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
                            label="Код"
                            value={formData.code}
                            onChange={(e) => setFormData({ ...formData, code: e.target.value })}
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
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={formData.is_final}
                                    onChange={(e) => setFormData({ ...formData, is_final: e.target.checked })}
                                />
                            }
                            label="Финальный"
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose}>Отмена</Button>
                    <Button onClick={handleSubmit} variant="contained" color="primary">
                        {editingStatus ? 'Сохранить' : 'Создать'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}; 