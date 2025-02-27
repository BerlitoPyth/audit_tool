import React, { useState, useEffect } from 'react';
import { 
  Typography, Grid, Paper, Box, Button, 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Card, CardContent, CardActions, Divider, Chip, Alert
} from '@mui/material';
import { 
  CloudUpload as UploadIcon,
  Assessment as AnalysisIcon,
  Description as ReportIcon,
  ArrowForward as ArrowIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { analysisService } from '../services/api';

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState({
    totalFiles: 0,
    totalAnomalies: 0
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Récupérer la liste des fichiers
        const filesData = await analysisService.listFiles();
        setFiles(filesData);
        
        // Calculer les statistiques de base
        setStats({
          totalFiles: filesData.length,
          totalAnomalies: 0 // Cette valeur devrait être calculée à partir des résultats d'analyse
        });
        
      } catch (err) {
        console.error("Erreur lors du chargement des données:", err);
        setError(err.message || "Une erreur est survenue lors du chargement des données.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  return (
    <Box>
      {/* En-tête avec bouton d'upload */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 4 
      }}>
        <Typography variant="h4">
          Tableau de bord
        </Typography>
        <Button
          variant="contained"
          startIcon={<UploadIcon />}
          onClick={() => navigate('/files')}
        >
          Uploader un fichier
        </Button>
      </Box>
      
      {/* Message d'erreur le cas échéant */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {/* Cartes statistiques */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Fichiers analysés
            </Typography>
            <Typography variant="h3">
              {stats.totalFiles}
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Anomalies détectées
            </Typography>
            <Typography variant="h3">
              {stats.totalAnomalies}
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <Box 
              sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                justifyContent: 'center', 
                height: '100%' 
              }}
            >
              <Typography variant="body1" paragraph>
                Commencez par uploader un fichier FEC pour analyse
              </Typography>
              <Button
                variant="contained"
                startIcon={<UploadIcon />}
                onClick={() => navigate('/files')}
              >
                Uploader un fichier
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Liste des fichiers récents */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Fichiers récents
        </Typography>
        
        {loading ? (
          <Typography variant="body1" color="text.secondary">
            Chargement des fichiers...
          </Typography>
        ) : files.length === 0 ? (
          <Typography variant="body1" color="text.secondary">
            Aucun fichier uploadé pour le moment
          </Typography>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nom du fichier</TableCell>
                  <TableCell>Date d'upload</TableCell>
                  <TableCell>Taille</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {files.slice(0, 5).map((file) => (
                  <TableRow key={file.file_id}>
                    <TableCell>{file.filename}</TableCell>
                    <TableCell>
                      {new Date(file.upload_timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {(file.size_bytes / 1024 / 1024).toFixed(2)} Mo
                    </TableCell>
                    <TableCell>
                      <Button 
                        variant="outlined"
                        size="small"
                        endIcon={<ArrowIcon />}
                        onClick={() => navigate(`/analysis/${file.file_id}`)}
                      >
                        Voir l'analyse
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        
        {files.length > 0 && (
          <Box sx={{ mt: 2, textAlign: 'right' }}>
            <Button
              variant="text"
              endIcon={<ArrowIcon />}
              onClick={() => navigate('/files')}
            >
              Voir tous les fichiers
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default Dashboard;
