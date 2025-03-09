import React from 'react';
import { Box, Container, Typography } from '@mui/material';
import { TaskTypeSettings } from '../components/TaskTypeSettings';
import { StatusSettings } from '../components/StatusSettings';
import { PrioritySettings } from '../components/PrioritySettings';
import { DurationSettings } from '../components/DurationSettings';

export const SettingsPage: React.FC = () => {
    return (
        <Container maxWidth="md">
            <Box py={4}>
                <Typography variant="h4" gutterBottom>
                    Настройки
                </Typography>
                
                <Box mb={4}>
                    <TaskTypeSettings />
                </Box>
                
                <Box mb={4}>
                    <StatusSettings />
                </Box>
                
                <Box mb={4}>
                    <PrioritySettings />
                </Box>
                
                <Box mb={4}>
                    <DurationSettings />
                </Box>
            </Box>
        </Container>
    );
}; 