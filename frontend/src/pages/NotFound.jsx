import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';

function NotFound() {
  const navigate = useNavigate();

  return (
    <Box sx={{ textAlign: 'center', mt: 8 }}>
      <Typography variant="h2" gutterBottom>
        404
      </Typography>
      <Typography variant="h5" gutterBottom>
        Page non trouvée
      </Typography>
      <Button 
        variant="contained" 
        onClick={() => navigate('/')}
        sx={{ mt: 2 }}
      >
        Retour à l'accueil
      </Button>
    </Box>
  );
}

export default NotFound;
