import React, { useState, useRef } from 'react';
import { 
  Box, Typography, Button, Paper, Grid, TextField, 
  Alert, AlertTitle, CircularProgress, List, ListItem,
  ListItemIcon, ListItemText, Divider, Chip
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircleOutline as CheckIcon,
  InsertDriveFile as FileIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';
import { analysisService } from '../services/api';
import { useNavigate } from 'react-router-dom';

function FileUpload() {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [uploadedFileId, setUploadedFileId] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Veuillez sélectionner un fichier");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await analysisService.uploadFile(file, description);
      
      setSuccess(true);
      setUploadedFileId(response.file_id);
      
      // Réinitialiser l'interface après le succès
      setFile(null);
      setDescription('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
    } catch (err) {
      console.error("Erreur lors de l'upload:", err);
      setError(err.message || "Une erreur est survenue lors de l'upload du fichier");
    } finally {
      setLoading(false);
    }
  };

  const viewAnalysis = () => {
    if (uploadedFileId) {
      navigate(`/analysis/${uploadedFileId}`);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Upload de fichier
      </Typography>
      
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Sélectionnez un fichier à analyser
        </Typography>
        
        <Typography variant="body2" color="text.secondary" paragraph>
          Formats acceptés: .csv, .txt (fichiers FEC), .xlsx, .xls (fichiers Excel)
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Box
              sx={{
                border: '2px dashed #ccc',
                borderRadius: 1,
                p: 3,
                textAlign: 'center',
                mb: 3,
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: '#f5f5f5'
                }
              }}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
            >
              <input
                type="file"
                hidden
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".csv,.txt,.xlsx,.xls"
              />
              <UploadIcon fontSize="large" color="primary" />
              <Typography variant="body1" sx={{ mt: 1 }}>
                Cliquez pour sélectionner un fichier ou glissez-déposez ici
              </Typography>
              
              {file && (
                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <FileIcon color="primary" sx={{ mr: 1 }} />
                  <Typography>
                    {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </Typography>
                </Box>
              )}
            </Box>
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              label="Description (optionnelle)"
              variant="outlined"
              fullWidth
              multiline
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ajoutez une description pour ce fichier"
            />
          </Grid>
          
          <Grid item xs={12}>
            <Button
              variant="contained"
              color="primary"
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <UploadIcon />}
              onClick={handleUpload}
              disabled={!file || loading}
              fullWidth
              size="large"
            >
              {loading ? 'Upload en cours...' : 'Uploader le fichier'}
            </Button>
          </Grid>
        </Grid>
        
        {error && (
          <Alert severity="error" sx={{ mt: 3 }}>
            <AlertTitle>Erreur</AlertTitle>
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert severity="success" sx={{ mt: 3 }}>
            <AlertTitle>Succès</AlertTitle>
            Le fichier a été uploadé avec succès !
            <Box sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                color="success"
                startIcon={<DescriptionIcon />}
                onClick={viewAnalysis}
              >
                Voir l'analyse
              </Button>
            </Box>
          </Alert>
        )}
      </Paper>
      
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Conseils pour l'upload de fichiers
        </Typography>
        
        <List>
          <ListItem>
            <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
            <ListItemText 
              primary="Formats de fichiers acceptés" 
              secondary="Fichiers FEC (.csv, .txt) ou fichiers Excel (.xlsx, .xls)" 
            />
          </ListItem>
          
          <Divider component="li" />
          
          <ListItem>
            <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
            <ListItemText 
              primary="Taille maximale" 
              secondary="100 MB par fichier" 
            />
          </ListItem>
          
          <Divider component="li" />
          
          <ListItem>
            <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
            <ListItemText 
              primary="Structure des données" 
              secondary="Assurez-vous que votre fichier suit la structure standard des fichiers FEC ou contient des données financières dans un format tabulaire." 
            />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
}

export default FileUpload;