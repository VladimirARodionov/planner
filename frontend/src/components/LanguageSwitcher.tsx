import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Menu,
  MenuItem,
  ListItemText,
  Typography
} from '@mui/material';
import { Language as LanguageIcon } from '@mui/icons-material';

export const LanguageSwitcher: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const changeLanguage = (language: string) => {
    i18n.changeLanguage(language);
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