import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Container, Typography, Card, CardContent, List, ListItem, ListItemIcon, ListItemText, Divider } from '@mui/material';
import { Assignment, Schedule, PriorityHigh, Category } from '@mui/icons-material';

export const AboutPage: React.FC = () => {
  const { t } = useTranslation();
  
  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          {t('about.title')}
        </Typography>

        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>
              {t('common.app_name')}
            </Typography>
            <Typography variant="body1" paragraph>
              {t('about.description')}
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              {t('about.features')}
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <Assignment />
                </ListItemIcon>
                <ListItemText 
                  primary={t('about.task_management')} 
                  secondary={t('about.task_management_desc')}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Category />
                </ListItemIcon>
                <ListItemText 
                  primary={t('about.categorization')} 
                  secondary={t('about.categorization_desc')}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <PriorityHigh />
                </ListItemIcon>
                <ListItemText 
                  primary={t('about.priorities')} 
                  secondary={t('about.priorities_desc')}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <Schedule />
                </ListItemIcon>
                <ListItemText 
                  primary={t('about.deadlines')} 
                  secondary={t('about.deadlines_desc')}
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {t('about.app_version')}
            </Typography>
            <Typography variant="body1">
              1.0.0
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              {t('about.copyright')}
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}; 