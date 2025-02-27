import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Container, Grid, Typography, Paper, Box, Button, 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, CircularProgress, Divider, Alert
} from '@mui/material';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend
} from 'recharts';
import {
  CloudUpload as UploadIcon,
  Assessment as AnalysisIcon,
  Description as ReportIcon,
  ArrowBack as BackIcon
} from '@mui/icons-material';
import { analysisService } from '../services/api';

// Palette de couleurs pour les graphiques
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

// Formater les types d'anomalie pour l'affichage
const formatAnomalyType = (type) => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Obtenir une couleur basée sur le score de confiance
const getSeverityColor = (confidenceScore) => {
  if (confidenceScore >= 0.8) return 'error';
  if (confidenceScore >= 0.6) return 'warning';
  if (confidenceScore >= 0.4) return 'info';
  return 'success';
};

const Analysis = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [anomalyStats, setAnomalyStats] = useState({
    byType: {},
    bySeverity: { high: 0, medium: 0, low: 0 }
  });
  
  // Chargement initial des données
  useEffect(() => {
    const fetchData = async () => {
      if (!fileId) {
        // Si pas de fileId, redirigez vers la liste des fichiers
        navigate('/files');
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        
        // Récupérer la liste des fichiers pour obtenir les infos sur celui-ci
        const files = await analysisService.listFiles();
        const currentFile = files.find(file => file.file_id === fileId);
        
        if (!currentFile) {
          throw new Error(`Fichier avec l'ID ${fileId} non trouvé.`);
        }
        
        setFileInfo(currentFile);
        
        // Récupérer les résultats d'analyse
        try {
          const results = await analysisService.getAnalysisResults(fileId);
          setAnalysisResults(results);
          
          // Calculer les statistiques par type et par sévérité
          const statsByType = {};
          const statsBySeverity = { high: 0, medium: 0, low: 0 };
          
          results.anomalies.forEach(anomaly => {
            // Stats par type
            if (!statsByType[anomaly.type]) {
              statsByType[anomaly.type] = 0;
            }
            statsByType[anomaly.type]++;
            
            // Stats par sévérité
            if (anomaly.confidence_score >= 0.8) {
              statsBySeverity.high++;
            } else if (anomaly.confidence_score >= 0.5) {
              statsBySeverity.medium++;
            } else {
              statsBySeverity.low++;
            }
          });
          
          setAnomalyStats({ byType: statsByType, bySeverity: statsBySeverity });
        } catch (analysisError) {
          console.error("Erreur lors du chargement des résultats d'analyse:", analysisError);
          // Ne pas considérer cela comme une erreur fatale
          // Il est possible que l'analyse n'ait pas encore été effectuée
        }
        
      } catch (err) {
        console.error("Erreur lors du chargement des données:", err);
        setError(err.message || "Une erreur est survenue lors du chargement des données.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [fileId, navigate]);
  
  // Lancer une nouvelle analyse
  const startNewAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await analysisService.startAnalysis(fileId);
      
      // Rediriger vers la page de statut ou rafraîchir après un délai
      setTimeout(() => {
        window.location.reload();
      }, 3000);
      
    } catch (err) {
      console.error("Erreur lors du lancement de l'analyse:", err);
      setError(err.message || "Une erreur est survenue lors du lancement de l'analyse.");
    } finally {
      setLoading(false);
    }
  };
  
  // Transformation des données pour les graphiques
  const getTypeChartData = () => {
    return Object.entries(anomalyStats.byType).map(([type, count]) => ({
      name: formatAnomalyType(type),
      value: count
    }));
  };
  
  const getSeverityChartData = () => {
    return [
      { name: 'Haute', value: anomalyStats.bySeverity.high },
      { name: 'Moyenne', value: anomalyStats.bySeverity.medium },
      { name: 'Basse', value: anomalyStats.bySeverity.low }
    ];
  };
  
  // Affichage pendant le chargement
  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8 }}>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 2 }}>Chargement des données d'analyse...</Typography>
        </Box>
      </Container>
    );
  }
  
  // Affichage en cas d'erreur
  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button 
          variant="contained" 
          startIcon={<BackIcon />} 
          onClick={() => navigate('/files')}
        >
          Retour à la liste des fichiers
        </Button>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      {/* En-tête */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="h5" gutterBottom>
              Analyse du fichier : {fileInfo?.filename}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Uploadé le : {new Date(fileInfo?.upload_timestamp).toLocaleString()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Taille : {(fileInfo?.size_bytes / 1024 / 1024).toFixed(2)} Mo
            </Typography>
          </Grid>
          <Grid item xs={12} md={4} sx={{ textAlign: 'right' }}>
            <Button 
              variant="outlined" 
              startIcon={<BackIcon />}
              onClick={() => navigate('/files')}
              sx={{ mr: 2 }}
            >
              Retour
            </Button>
            <Button 
              variant="contained"
              startIcon={<AnalysisIcon />}
              onClick={startNewAnalysis}
              color="primary"
            >
              Relancer l'analyse
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      {/* Si aucun résultat d'analyse n'est disponible */}
      {!analysisResults && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            Aucune analyse n'a été effectuée pour ce fichier
          </Typography>
          <Typography variant="body1" paragraph sx={{ mb: 3 }}>
            Vous pouvez lancer une nouvelle analyse pour détecter les anomalies potentielles.
          </Typography>
          <Button
            variant="contained"
            startIcon={<AnalysisIcon />}
            onClick={startNewAnalysis}
            size="large"
          >
            Lancer l'analyse
          </Button>
        </Paper>
      )}
      
      {/* Résultats d'analyse */}
      {analysisResults && (
        <>
          {/* Résumé des anomalies */}
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Répartition par type d'anomalie
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={getTypeChartData()}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                      label={({name, percent}) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {getTypeChartData().map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `${value} anomalies`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Répartition par sévérité
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={getSeverityChartData()}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                      label={({name, percent}) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      <Cell key="cell-high" fill="#f44336" />
                      <Cell key="cell-medium" fill="#ff9800" />
                      <Cell key="cell-low" fill="#4caf50" />
                    </Pie>
                    <Tooltip formatter={(value) => `${value} anomalies`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>
          
          {/* Liste des anomalies */}
          <Paper sx={{ p: 3, mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Liste des anomalies détectées ({analysisResults.anomalies.length})
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Confiance</TableCell>
                    <TableCell>Lignes concernées</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analysisResults.anomalies.map((anomaly) => (
                    <TableRow key={anomaly.id}>
                      <TableCell>
                        <Chip 
                          label={formatAnomalyType(anomaly.type)} 
                          color="primary" 
                          variant="outlined" 
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{anomaly.description}</TableCell>
                      <TableCell>
                        <Chip 
                          label={`${(anomaly.confidence_score * 100).toFixed(0)}%`} 
                          color={getSeverityColor(anomaly.confidence_score)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {anomaly.line_numbers?.join(', ') || 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
          
          {/* Actions pour les rapports */}
          <Paper sx={{ p: 3, mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Générer un rapport
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <Button 
                  variant="outlined" 
                  startIcon={<ReportIcon />} 
                  fullWidth
                  onClick={() => alert('Génération du rapport sommaire...')}
                >
                  Rapport sommaire
                </Button>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Button 
                  variant="outlined" 
                  startIcon={<ReportIcon />} 
                  fullWidth
                  onClick={() => alert('Génération du rapport détaillé...')}
                >
                  Rapport détaillé
                </Button>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Button 
                  variant="outlined" 
                  startIcon={<ReportIcon />} 
                  fullWidth
                  onClick={() => alert('Export des données...')}
                >
                  Exporter les données
                </Button>
              </Grid>
            </Grid>
          </Paper>
        </>
      )}
    </Container>
  );
};

export default Analysis;
