import React from 'react';
import { Box, Container, Typography, Card, CardContent, List, ListItem, ListItemIcon, ListItemText, Divider } from '@mui/material';
import { Assignment, Schedule, PriorityHigh, Category } from '@mui/icons-material';

export const AboutPage: React.FC = () => {
  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          О приложении
        </Typography>

        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              Планировщик задач
            </Typography>
            <Typography variant="body1" paragraph>
              Это приложение поможет вам эффективно управлять задачами и организовать свое время. 
              Вы можете создавать, редактировать и отслеживать задачи с различными параметрами.
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              Основные возможности:
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <Assignment />
                </ListItemIcon>
                <ListItemText 
                  primary="Управление задачами" 
                  secondary="Создание, редактирование и удаление задач с гибкой системой настроек"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Category />
                </ListItemIcon>
                <ListItemText 
                  primary="Категоризация" 
                  secondary="Распределение задач по типам и статусам"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <PriorityHigh />
                </ListItemIcon>
                <ListItemText 
                  primary="Приоритеты" 
                  secondary="Установка приоритетов для задач"
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Schedule />
                </ListItemIcon>
                <ListItemText 
                  primary="Дедлайны" 
                  secondary="Установка сроков выполнения и автоматический расчет дедлайнов на основе длительности"
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Версия приложения
            </Typography>
            <Typography variant="body1">
              1.0.0
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              © 2024 Планировщик задач. Все права защищены.
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}; 