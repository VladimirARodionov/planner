import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Menu,
  MenuItem,
  ListItemText,
  Typography
} from '@mui/material';
import { Language as LanguageIcon } from '@mui/icons-material';
import { AuthAPI } from '../api/auth';

export const LanguageSwitcher: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // Проверяем, авторизован ли пользователь
  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(token !== null);
    
    // Если пользователь авторизован, загружаем его язык с сервера
    if (token) {
      const loadUserLanguage = async () => {
        try {
          const language = await AuthAPI.getUserLanguage();
          // Меняем язык только если он отличается от текущего
          if (language && language !== i18n.language) {
            i18n.changeLanguage(language);
          }
        } catch (error) {
          console.error('Error loading user language:', error);
        }
      };
      
      loadUserLanguage();
    }
  }, [i18n]);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const changeLanguage = async (language: string) => {
    // Меняем язык в i18n
    await i18n.changeLanguage(language);
    
    // Если пользователь авторизован, сохраняем выбор на сервере
    if (isAuthenticated) {
      try {
        await AuthAPI.setUserLanguage(language);
      } catch (error) {
        console.error('Error saving language preference:', error);
      }
    }
    
    handleClose();
  };

  return (
    <>
      <Button
        color="inherit"
        onClick={handleClick}
        startIcon={<LanguageIcon />}
        sx={{ textTransform: 'none' }}
      >
        <Typography variant="body2">
          {i18n.language === 'ru' ? 'RU' : 'EN'}
        </Typography>
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
      >
        <MenuItem 
          onClick={() => changeLanguage('ru')}
          selected={i18n.language === 'ru'}
        >
          <ListItemText primary={t('language.ru')} />
        </MenuItem>
        <MenuItem 
          onClick={() => changeLanguage('en')}
          selected={i18n.language === 'en'}
        >
          <ListItemText primary={t('language.en')} />
        </MenuItem>
      </Menu>
    </>
  );
}; 