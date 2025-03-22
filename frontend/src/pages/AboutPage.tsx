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