import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Menu,
  MenuItem,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  TextField,
  Box,
  Typography,
  IconButton,
  SelectChangeEvent,
} from '@mui/material';
import { AccessTime as AccessTimeIcon, Search as SearchIcon, Close as CloseIcon } from '@mui/icons-material';
import { AuthAPI, Timezone } from '../api/auth';

export const TimezoneSwitcher: React.FC = () => {
  const { t } = useTranslation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentTimezone, setCurrentTimezone] = useState<string>('');
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);
  const [allTimezones, setAllTimezones] = useState<Timezone[]>([]);
  const [filteredTimezones, setFilteredTimezones] = useState<Timezone[]>([]);
  const [searchText, setSearchText] = useState<string>('');
  const [selectedGroup, setSelectedGroup] = useState<string>('All');
  const [groups, setGroups] = useState<string[]>(['All']);

  // Проверяем, авторизован ли пользователь и получаем его текущий часовой пояс
  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(token !== null);
    
    if (token) {
      const loadUserTimezone = async () => {
        try {
          const timezone = await AuthAPI.getUserTimezone();
          setCurrentTimezone(timezone);
        } catch (error) {
          console.error('Error loading user timezone:', error);
        }
      };
      
      loadUserTimezone();
    } else {
      // Используем часовой пояс браузера
      setCurrentTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    }
  }, []);

  // Загружаем список всех часовых поясов
  useEffect(() => {
    const fetchTimezones = async () => {
      try {
        const timezones = await AuthAPI.getTimezones();
        setAllTimezones(timezones);
        setFilteredTimezones(timezones);
        
        // Извлекаем уникальные группы часовых поясов
        const uniqueGroupsSet = new Set<string>();
        timezones.forEach(tz => uniqueGroupsSet.add(tz.group));
        const uniqueGroups = ['All', ...Array.from(uniqueGroupsSet)];
        setGroups(uniqueGroups);
      } catch (error) {
        console.error('Error fetching timezones:', error);
      }
    };
    
    if (isAuthenticated) {
      fetchTimezones();
    }
  }, [isAuthenticated]);

  // Фильтрация часовых поясов при изменении поискового запроса или группы
  useEffect(() => {
    let filtered = allTimezones;
    
    // Фильтруем по группе
    if (selectedGroup !== 'All') {
      filtered = filtered.filter(tz => tz.group === selectedGroup);
    }
    
    // Фильтруем по поисковому запросу
    if (searchText) {
      const search = searchText.toLowerCase();
      filtered = filtered.filter(tz => 
        tz.label.toLowerCase().includes(search) || 
        tz.value.toLowerCase().includes(search)
      );
    }
    
    setFilteredTimezones(filtered);
  }, [searchText, selectedGroup, allTimezones]);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const openTimezoneDialog = () => {
    setDialogOpen(true);
    handleClose();
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setSearchText('');
    setSelectedGroup('All');
  };

  const handleGroupChange = (event: SelectChangeEvent<string>) => {
    setSelectedGroup(event.target.value);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(event.target.value);
  };

  const handleTimezoneSelect = async (timezone: string) => {
    if (timezone === currentTimezone) {
      handleDialogClose();
      return;
    }
    
    if (isAuthenticated) {
      try {
        const success = await AuthAPI.setUserTimezone(timezone);
        if (success) {
          setCurrentTimezone(timezone);
        }
      } catch (error) {
        console.error('Error saving timezone preference:', error);
      }
    } else {
      setCurrentTimezone(timezone);
    }
    
    handleDialogClose();
  };

  const formatTimezone = (timezone: string): string => {
    const now = new Date();
    try {
      const offset = new Intl.DateTimeFormat('en', {
        timeZone: timezone,
        timeZoneName: 'short'
      }).format(now).split(' ')[1];
      
      return offset || timezone;
    } catch (error) {
      return timezone;
    }
  };

  return (
    <>
      <Button
        color="inherit"
        onClick={handleClick}
        startIcon={<AccessTimeIcon />}
        sx={{ textTransform: 'none' }}
      >
        <Typography variant="body2">
          {formatTimezone(currentTimezone)}
        </Typography>
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
      >
        <MenuItem onClick={openTimezoneDialog}>
          <ListItemText primary={t('timezone.select')} />
        </MenuItem>
      </Menu>

      <Dialog 
        open={dialogOpen} 
        onClose={handleDialogClose}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          {t('timezone.select_timezone')}
          <IconButton
            aria-label="close"
            onClick={handleDialogClose}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', mb: 2, gap: 1 }}>
            <TextField
              fullWidth
              placeholder={t('timezone.search')}
              value={searchText}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />
              }}
              variant="outlined"
              size="small"
            />
            <FormControl sx={{ minWidth: 150 }} size="small">
              <InputLabel id="timezone-group-label">{t('timezone.group')}</InputLabel>
              <Select
                labelId="timezone-group-label"
                value={selectedGroup}
                label={t('timezone.group')}
                onChange={handleGroupChange}
              >
                {groups.map((group) => (
                  <MenuItem key={group} value={group}>
                    {group}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          
          <Box sx={{ 
            maxHeight: 300, 
            overflow: 'auto',
            border: '1px solid rgba(0, 0, 0, 0.12)',
            borderRadius: 1
          }}>
            {filteredTimezones.length > 0 ? (
              filteredTimezones.map((timezone) => (
                <MenuItem 
                  key={timezone.value} 
                  onClick={() => handleTimezoneSelect(timezone.value)}
                  selected={currentTimezone === timezone.value}
                  sx={{ 
                    py: 1.5,
                    borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
                    '&:last-child': { borderBottom: 'none' }
                  }}
                >
                  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="body1">
                      {timezone.label} ({formatTimezone(timezone.value)})
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {timezone.value}
                    </Typography>
                  </Box>
                </MenuItem>
              ))
            ) : (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  {t('timezone.no_results')}
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>{t('common.cancel')}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}; 