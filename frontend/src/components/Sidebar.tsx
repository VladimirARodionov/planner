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
  IconButton,
  useTheme,
  useMediaQuery
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
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
        mr: 1
      }}
    >
      <MenuIcon />
    </IconButton>
  );

  return (
    <>
      <MenuButton />
      <Drawer
        variant="persistent"
        anchor="left"
        open={open}
        sx={{
          //width: open ? drawerWidth : 0,
          width: 0,
          flexShrink: 0,
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            transition: theme.transitions.create(['transform', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            ...(!open && {
              transform: 'translateX(-100%)',
              visibility: 'hidden',
            }),
            ...(open && {
              transform: 'translateX(0)',
              visibility: 'visible',
            }),
          },
        }}
      >
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          minHeight: { xs: 56, sm: 64 },
          px: 2,
          py: 1
        }}>
          <Typography 
            variant="h6" 
            sx={{ 
              fontSize: { xs: '1.1rem', sm: '1.25rem' }
            }}
          >
            {t('common.app_name')}
          </Typography>
          <IconButton onClick={onClose} size="small">
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
                  if (isMobile) {
                    onClose();
                  }
                }}
                sx={{
                  minHeight: 48,
                  px: 2.5,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    '&:hover': {
                      backgroundColor: 'primary.light',
                    }
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  primary={item.title} 
                  primaryTypographyProps={{
                    fontSize: { xs: '0.9rem', sm: '1rem' }
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
    </>
  );
}; 