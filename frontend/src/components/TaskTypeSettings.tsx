import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
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
    Card,
    CardHeader,
    Divider
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';

export const TaskTypeSettings: React.FC = () => {
    const { t } = useTranslation();
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
            alert(t('settings.error_saving_type'));
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm(t('settings.delete_type_confirmation'))) {
            try {
                await TasksAPI.deleteTaskType(id);
                loadTaskTypes();
            } catch (error) {
                console.error('Error deleting task type:', error);
                alert(t('settings.error_deleting_type'));
            }
        }
    };

    return (
        <Card variant="outlined">
            <CardHeader 
                title={t('settings.task_types')}
                action={
                    <Button
                        color="primary"
                        startIcon={<AddIcon />}
                        onClick={() => handleOpen()}
                    >
                        {t('settings.add_task_type')}
                    </Button>
                }
            />
            <Divider />

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
                                title={t('common.edit')}
                            >
                                <EditIcon />
                            </IconButton>
                            <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={() => handleDelete(type.id)}
                                title={t('common.delete')}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {editingType ? t('settings.edit_task_type') : t('settings.add_task_type')}
                </DialogTitle>
                <DialogContent>
                    <Box display="flex" flexDirection="column" gap={2} mt={2}>
                        <TextField
                            label={t('settings.name')}
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label={t('tasks.description')}
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            fullWidth
                            multiline
                            rows={2}
                        />
                        <TextField
                            label={t('settings.color')}
                            type="color"
                            value={formData.color}
                            onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label={t('settings.position_number')}
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
                        {editingType ? t('common.save') : t('common.create')}
                    </Button>
                </DialogActions>
            </Dialog>
        </Card>
    );
}; 