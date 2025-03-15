import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
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
    Card,
    CardHeader,
    Divider,
    InputAdornment
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import { ColorPicker } from './ColorPicker';

export const PrioritySettings: React.FC = () => {
    const { t } = useTranslation();
    const [priorities, setPriorities] = useState<Priority[]>([]);
    const [open, setOpen] = useState(false);
    const [editingPriority, setEditingPriority] = useState<Priority | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        color: '#1976D2',
        position: 0
    });

    useEffect(() => {
        loadPriorities();
    }, []);

    const loadPriorities = async () => {
        try {
            const data = await TasksAPI.getPriorities();
            console.log('Loaded priorities:', data);
            setPriorities(data);
        } catch (error) {
            console.error('Error loading priorities:', error);
        }
    };

    const handleOpen = (priority?: Priority) => {
        if (priority) {
            setEditingPriority(priority);
            setFormData({
                name: priority.name,
                color: priority.color || '#1976D2',
                position: priority.position || 0
            });
        } else {
            setEditingPriority(null);
            setFormData({
                name: '',
                color: '#1976D2',
                position: priorities.length + 1
            });
        }
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
    };

    const handleSubmit = async () => {
        try {
            if (editingPriority) {
                await TasksAPI.updatePriority(editingPriority.id, formData);
            } else {
                await TasksAPI.createPriority(formData);
            }
            loadPriorities();
            handleClose();
        } catch (error) {
            console.error('Error saving priority:', error);
            alert(t('settings.error_saving_priority'));
        }
    };

    const handleDelete = async (id: number) => {
        if (window.confirm(t('settings.delete_priority_confirmation'))) {
            try {
                await TasksAPI.deletePriority(id);
                loadPriorities();
            } catch (error) {
                console.error('Error deleting priority:', error);
                alert(t('settings.error_deleting_priority'));
            }
        }
    };

    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = event.target;
        setFormData({
            ...formData,
            [name]: value
        });
    };

    const handleColorChange = (color: string) => {
        setFormData({
            ...formData,
            color
        });
    };

    return (
        <Card variant="outlined">
            <CardHeader 
                title={t('settings.priorities')}
                action={
                    <Button 
                        startIcon={<AddIcon />} 
                        onClick={() => handleOpen()}
                        color="primary"
                    >
                        {t('settings.add_priority')}
                    </Button>
                }
            />
            <Divider />
            <List>
                {priorities.map(priority => (
                    <ListItem key={priority.id}>
                        <Box 
                            sx={{ 
                                width: 16, 
                                height: 16, 
                                borderRadius: '50%', 
                                backgroundColor: priority.color || '#ccc',
                                mr: 2
                            }} 
                        />
                        <ListItemText 
                            primary={priority.name}
                            secondary={t('settings.position', { position: priority.position })}
                        />
                        <ListItemSecondaryAction>
                            <IconButton edge="end" onClick={() => handleOpen(priority)} title={t('common.edit')}>
                                <EditIcon />
                            </IconButton>
                            <IconButton edge="end" onClick={() => handleDelete(priority.id)} title={t('common.delete')}>
                                <DeleteIcon />
                            </IconButton>
                        </ListItemSecondaryAction>
                    </ListItem>
                ))}
            </List>

            <Dialog open={open} onClose={handleClose}>
                <DialogTitle>
                    {editingPriority 
                        ? t('settings.edit_priority') 
                        : t('settings.add_priority')
                    }
                </DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        margin="dense"
                        name="name"
                        label={t('settings.priority_name')}
                        type="text"
                        fullWidth
                        value={formData.name}
                        onChange={handleChange}
                    />
                    <Box sx={{ mt: 2, mb: 1 }}>
                        <ColorPicker 
                            color={formData.color} 
                            onChange={handleColorChange}
                            label={t('settings.color')}
                        />
                    </Box>
                    <TextField
                        margin="dense"
                        name="position"
                        label={t('settings.position_number')}
                        type="number"
                        fullWidth
                        value={formData.position}
                        onChange={handleChange}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">#</InputAdornment>
                            ),
                        }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleClose}>{t('common.cancel')}</Button>
                    <Button onClick={handleSubmit} color="primary">{t('common.save')}</Button>
                </DialogActions>
            </Dialog>
        </Card>
    );
}; 