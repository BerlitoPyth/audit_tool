import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, Container, Paper, Typography, Button, TextField, 
  Grid, LinearProgress, Alert, AlertTitle, Divider,
  Stepper, Step, StepLabel, StepContent, Card, CardContent
} from '@mui/material';
import { 
  CloudUpload as UploadIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Description as FileIcon
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { analysisService } from '../services/api';

/**
 * Page d'upload de fichiers FEC
 * Permet de télécharger un fichier, puis de lancer une analyse
 */
const FileUpload = () => {
  const navigate = useNavigate();
  
  // États pour le formulaire et le process d'upload
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  
  // Configuration de la zone de drop pour les fichiers
  const onDrop = useCallback(acceptedFiles => {
    // Ne prendre que le premier fichier
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError(null);
    }
  }, []);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv', '.xls', '.xlsx'],
      'application/octet-stream': ['.fec']
    },
    maxSize: 100 * 1024 * 1024, // 100 MB max
    multiple: false
  });
  
  // Gérer le changement de description
  const handleDescriptionChange = (e) => {
    setDescription(e.target.value);
  };
  
  // Simuler la progression de l'upload
  const simulateProgress = () => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 10;
      if (progress > 95) {
        progress = 95;
        clearInterval(interval);
      }
      setUploadProgress(progress);
    }, 300);
    
    return interval;
  };
  
  // Gérer l'upload du fichier
  const handleUpload = async () => {
    if (!file) {
      setError('Veuillez sélectionner un fichier');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      setActiveStep(1);
      
      // Simuler la progression (car l'API ne nous donne pas de feedback en temps réel)
      const progressInterval = simulateProgress();
      
      // Appel API pour l'upload
      const result = await analysisService.uploadFile(file, description);
      
      // Arrêter la simulation et mettre la barre à 100%
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      if (result.error) {
        throw new Error(result.message || 'Erreur lors de l\'upload');
      }
      
      // Mettre à jour l'état avec le résultat
      setUploadResult(result);
      setActiveStep(2);
      
    } catch (err) {
      console.error('Erreur upload:', err);
      setError(err.message || 'Une erreur s\'est produite lors de l\'upload');
      setActiveStep(0);
    } finally {
      setLoading(false);
    }
  };
  
  // Lancer directement l'analyse après l'upload
  const handleStartAnalysis = async () => {
    if (!uploadResult || !uploadResult.file_id) {
      setError('Aucun fichier uploadé');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      setActiveStep(3);
      
      // Appel API pour démarrer l'analyse
      const result = await analysisService.startAnalysis(uploadResult.file_id);
      
      if (result.error) {
        throw new Error(result.message || 'Erreur lors du lancement de l\'analyse');
      }
      
      // Rediriger vers la page de détails du fichier
      navigate(`/analysis/${uploadResult.file_id}`);
      
    } catch (err) {
      console.error('Erreur analyse:', err);
      setError(err.message || 'Une erreur s\'est produite lors du lancement de l\'analyse');
    } finally {
      setLoading(false);
    }
  };
  
  // Étapes du processus d'upload et d'analyse
  const steps = [
    {
      label: 'Sélection du fichier',
      description: 'Sélectionnez un fichier FEC à analyser',
      content: (
        <Box sx={{ mt: 2 }}>
          <div
            {...getRootProps()}
            style={{
              border: `2px dashed ${isDragActive ? '#2196f3' : '#cccccc'}`,
              borderRadius: '4px',
              padding: '20px',
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive ? 'rgba(33, 150, 243, 0.1)' : '#fafafa',
              marginBottom: '20px'
            }}
          >
            <input {...getInputProps()} />
            <UploadIcon style={{ fontSize: 48, color: '#757575', marginBottom: '8px' }} />
            <Typography variant="h6" gutterBottom>
              Glissez-déposez un fichier ici
            </Typography>
            <Typography variant="body2" color="textSecondary">
              ou cliquez pour sélectionner un fichier
            </Typography>
            <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
              Formats acceptés: .csv, .xls, .xlsx, .fec (max 100 Mo)
            </Typography>
          </div>
          
          {file && (
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <FileIcon color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="subtitle1">{file.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {(file.size / (1024 * 1024)).toFixed(2)} Mo
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}
          
          <TextField
            label="Description (optionnelle)"
            multiline
            rows={3}
            fullWidth
            variant="outlined"
            value={description}
            onChange={handleDescriptionChange}
            disabled={loading}
            placeholder="Ajouter une description du fichier..."
            sx={{ mb: 3 }}
          />
          
          <Button
            variant="contained"
            color="primary"
            startIcon={<UploadIcon />}
            onClick={handleUpload}
            disabled={!file || loading}
            fullWidth
          >
            Uploader le fichier
          </Button>
        </Box>
      )
    },
    {
      label: 'Upload en cours',
      description: 'Le fichier est en cours d\'upload sur le serveur',
      content: (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body1" gutterBottom>
            Upload en cours de {file?.name}...
          </Typography>
          <Box sx={{ mt: 2, mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={uploadProgress} 
            />
            <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
              {Math.round(uploadProgress)}% terminé
            </Typography>
          </Box>
        </Box>
      )
    },
    {
      label: 'Upload terminé',
      description: 'Le fichier a été uploadé avec succès',
      content: (
        <Box sx={{ mt: 2 }}>
          <Alert severity="success" sx={{ mb: 3 }}>
            <AlertTitle>Succès</AlertTitle>
            Le fichier a été uploadé avec succès !
          </Alert>
          
          <Typography variant="subtitle1" gutterBottom>
            Informations sur le fichier:
          </Typography>
          
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">ID:</Typography>
            </Grid>
            <Grid item xs={8}>
              <Typography variant="body2">{uploadResult?.file_id}</Typography>
            </Grid>
            
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">Nom:</Typography>
            </Grid>
            <Grid item xs={8}>
              <Typography variant="body2">{uploadResult?.filename}</Typography>
            </Grid>
            
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">Taille:</Typography>
            </Grid>
            <Grid item xs={8}>
              <Typography variant="body2">
                {(uploadResult?.size_bytes / (1024 * 1024)).toFixed(2)} Mo
              </Typography>
            </Grid>
          </Grid>
          
          <Button
            variant="contained"
            color="primary"
            onClick={handleStartAnalysis}
            disabled={loading}
            fullWidth
          >
            Lancer l'analyse
          </Button>
        </Box>
      )
    },
    {
      label: 'Lancement de l\'analyse',
      description: 'L\'analyse du fichier est en cours de lancement',
      content: (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body1" gutterBottom>
            Lancement de l'analyse en cours...
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}>
            <LinearProgress sx={{ width: '50%' }} />
          </Box>
          <Typography variant="body2" color="textSecondary">
            Vous allez être redirigé vers la page d'analyse...
          </Typography>
        </Box>
      )
    }
  ];
  
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Upload d'un fichier FEC
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Uploadez un fichier FEC (Format d'Échange Comptable) pour l'analyser et détecter les anomalies potentielles.
        </Typography>
        
        <Divider sx={{ my: 3 }} />
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            <AlertTitle>Erreur</AlertTitle>
            {error}
          </Alert>
        )}
        
        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((step, index) => (
            <Step key={step.label}>
              <StepLabel>
                <Typography variant="subtitle1">{step.label}</Typography>
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="textSecondary">
                  {step.description}
                </Typography>
                {step.content}
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </Paper>
    </Container>
  );
};

export default FileUpload;