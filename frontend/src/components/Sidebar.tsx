import React from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Drawer, 
  List, 
  ListItem, 
  ListItemButton, 
  ListItemIcon, 
  ListItemText, 
  Divider, 
  Box, 
  Typography,
  IconButton
} from '@mui/material';
import { 
  List as ListIcon, 
  Settings as SettingsIcon, 
  Info as InfoIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon
} from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { useLocation } from 'react-router-dom';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  onOpen: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ open, onClose, onOpen }) => {
  const { t } = useTranslation();
  const location = useLocation();
  const drawerWidth = 240;

  // Определение списка пунктов меню с абсолютными путями
  const menuItems = [
    { title: t('sidebar.task_list'), path: '/', icon: <ListIcon /> },
    { title: t('sidebar.settings'), path: '/settings', icon: <SettingsIcon /> },
    { title: t('sidebar.about'), path: '/about', icon: <InfoIcon /> }
  ];

  // Кнопка открытия меню (показывается, когда меню закрыто)
  const MenuButton = () => (
    <IconButton
      color="inherit"
      aria-label="open menu"
      onClick={onOpen}
      edge="start"
      sx={{ 
        mr: 2, 
        display: { xs: open ? 'none' : 'flex', sm: open ? 'none' : 'flex' } 
      }}
    >
      <MenuIcon />
    </IconButton>
  );

  return (
    <>
      <MenuButton />
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 1 }}>
          <Typography variant="h6" sx={{ pl: 1 }}>
            {t('common.app_name')}
          </Typography>
          <IconButton onClick={onClose}>
            <ChevronLeftIcon />
          </IconButton>
        </Box>
        <Divider />
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.path} disablePadding>
              <ListItemButton 
                component={RouterLink}
                to={item.path}
                selected={location.pathname === item.path}
                onClick={() => {
                  if (window.innerWidth < 600) {
                    onClose();
                  }
                }}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    '&:hover': {
                      backgroundColor: 'primary.light',
                    }
                  }
                }}
              >
                <ListItemIcon>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.title} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
    </>
  );
}; 