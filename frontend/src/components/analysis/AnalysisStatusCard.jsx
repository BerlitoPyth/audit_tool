import React from 'react';
import { 
  Card, CardContent, CardHeader, Typography, Box, 
  LinearProgress, Grid, Chip, Divider, Button, Paper
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import {
  QueryStats as AnalysisIcon,
  Schedule as PendingIcon,
  Sync as ProcessingIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon
} from '@mui/icons-material';

// Fonctions utilitaires pour le composant
const getStatusIcon = (status) => {
  switch (status) {
    case 'pending':
      return <PendingIcon color="warning" />;
    case 'processing':
      return <ProcessingIcon color="info" />;
    case 'completed':
      return <CompletedIcon color="success" />;
    case 'failed':
      return <ErrorIcon color="error" />;
    default:
      return <AnalysisIcon color="primary" />;
  }
};

const getStatusColor = (status) => {
  switch (status) {
    case 'pending':
      return 'warning';
    case 'processing':
      return 'info';
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    default:
      return 'default';
  }
};

const getStatusLabel = (status) => {
  switch (status) {
    case 'pending':
      return 'En attente';
    case 'processing':
      return 'En cours';
    case 'completed':
      return 'Terminé';
    case 'failed':
      return 'Échec';
    default:
      return 'Inconnu';
  }
};

/**
 * Composant pour afficher l'état actuel d'une analyse en cours
 * 
 * @param {Object} props - Propriétés du composant
 * @param {Object} props.status - Statut actuel de l'analyse
 * @param {Object} props.fileMetadata - Métadonnées du fichier analysé
 */
const AnalysisStatusCard = ({ status, fileMetadata }) => {
  const navigate = useNavigate();
  
  // Si pas de statut, ne rien afficher
  if (!status) {
    return null;
  }
  
  return (
    <Paper sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Analyse en cours</Typography>
            <Chip 
              label={getStatusLabel(status.status)}
              color={getStatusColor(status.status)}
              size="small"
            />
          </Box>
        </Grid>

        {fileMetadata && (
          <Grid item xs={12}>
            <Typography variant="body2" color="textSecondary">
              Fichier: {fileMetadata.filename}
            </Typography>
          </Grid>
        )}
        
        <Grid item xs={12}>
          <Box sx={{ mb: 1, mt: 2 }}>
            <Typography variant="body2" color="textSecondary">
              Progression: {Math.round(status.progress * 100)}%
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={status.progress * 100} 
              sx={{ mt: 1, mb: 2 }}
            />
          </Box>
          
          {status.message && (
            <Typography variant="body2" color="textSecondary">
              {status.message}
            </Typography>
          )}
        </Grid>

        <Grid item xs={12}>
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color="textSecondary">
              Démarré à: {new Date(status.started_at).toLocaleString()}
            </Typography>
            {status.completed_at && (
              <Typography variant="body2" color="textSecondary">
                Terminé à: {new Date(status.completed_at).toLocaleString()}
              </Typography>
            )}
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default AnalysisStatusCard;