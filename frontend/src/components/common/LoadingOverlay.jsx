import React from 'react';
import { Backdrop, CircularProgress, Typography, Box } from '@mui/material';

const LoadingOverlay = ({ message = 'Chargement...' }) => {
  return (
    <Backdrop
      open={true}
      sx={{
        color: '#fff',
        zIndex: (theme) => theme.zIndex.drawer + 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2
      }}
    >
      <CircularProgress color="inherit" />
      <Typography variant="h6" component="div">
        {message}
      </Typography>
    </Backdrop>
  );
};

export default LoadingOverlay;
