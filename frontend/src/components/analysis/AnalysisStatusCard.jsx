import React from 'react';
import { 
  Card, CardContent, CardHeader, Typography, Box, 
  LinearProgress, Grid, Chip, Divider, Button
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
    <Card raised>
      <CardHeader 
        title="Analyse en cours"
        titleTypographyProps={{ variant: 'h5' }}
        avatar={getStatusIcon(status.status)}
      />
      
      <CardContent>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Fichier analysé
              </Typography>
              <Typography variant="body1">
                {fileMetadata?.filename || "Fichier inconnu"}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Taille: {fileMetadata ? `${(fileMetadata.size_bytes / (1024 * 1024)).toFixed(2)} Mo` : "Inconnue"}
              </Typography>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Statut de l'analyse
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Chip 
                  label={getStatusLabel(status.status)} 
                  color={getStatusColor(status.status)}
                  size="small"
                  sx={{ mr: 2 }}
                />
                <Typography variant="body2">
                  {status.message || "Analyse en cours..."}
                </Typography>
              </Box>
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Progression
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Box sx={{ width: '100%', mr: 1 }}>
                  <LinearProgress 
                    variant="determinate" 
                    value={status.progress * 100} 
                    color={getStatusColor(status.status)}
                    sx={{ height: 10, borderRadius: 5 }}
                  />
                </Box>
                <Box sx={{ minWidth: 35 }}>
                  <Typography variant="body2" color="textSecondary">
                    {`${Math.round(status.progress * 100)}%`}
                  </Typography>
                </Box>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Informations temporelles
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    Démarré le:
                  </Typography>
                  <Typography variant="body2">
                    {status.started_at ? new Date(status.started_at).toLocaleString() : "N/A"}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    Estimé:
                  </Typography>
                  <Typography variant="body2">
                    {status.status === 'processing' ? (
                      status.progress > 0 
                        ? `~${Math.round((1 - status.progress) / (status.progress) * 
                            ((new Date() - new Date(status.started_at)) / 1000 / 60))} minutes`
                        : "Calcul en cours..."
                    ) : "N/A"}
                  </Typography>
                </Grid>
              </Grid>
            </Box>
          </Grid>
          
          <Grid item xs={12} sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/files')}
              sx={{ mr: 2 }}
            >
              Retour à la liste des fichiers
            </Button>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default AnalysisStatusCard;