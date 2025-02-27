import React from 'react';
import { Snackbar, Alert } from '@mui/material';
import { useAppContext } from '../../context/AppContext';

const Notification = () => {
  const { notification } = useAppContext();

  if (!notification) return null;

  return (
    <Snackbar
      open={true}
      autoHideDuration={6000}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
    >
      <Alert severity={notification.type} elevation={6} variant="filled">
        {notification.message}
      </Alert>
    </Snackbar>
  );
};

export default Notification;
