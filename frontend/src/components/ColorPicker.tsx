import React from 'react';
import { Box, TextField, Typography } from '@mui/material';

interface ColorPickerProps {
  color: string;
  onChange: (color: string) => void;
  label?: string;
}

export const ColorPicker: React.FC<ColorPickerProps> = ({ color, onChange, label }) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      {label && <Typography variant="body2">{label}</Typography>}
      <TextField
        type="color"
        value={color}
        onChange={(e) => onChange(e.target.value)}
        sx={{ width: '64px' }}
      />
      <Typography variant="body2">{color}</Typography>
    </Box>
  );
}; 