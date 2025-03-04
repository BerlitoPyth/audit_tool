import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Container, Grid, Typography, Paper, Box, CircularProgress, 
  Chip, Table, TableBody, TableCell, TableContainer, TableHead, 
  TableRow, Divider, Button, Alert
} from '@mui/material';
import {
  PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend, ResponsiveContainer
} from 'recharts';
import { 
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  DateRange as DateIcon,
  AccountBalance as BalanceIcon,
  FileCopy as DuplicateIcon,
  Code as PatternIcon
} from '@mui/icons-material';

import { analysisService } from '../../services/api';
import AnomalyTable from './AnomalyTable';
import AnalysisStatusCard from './AnalysisStatusCard';
import LoadingOverlay from '../common/LoadingOverlay';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const getAnomalyIcon = (type) => {
  switch (type) {
    case 'balance_mismatch':
      return <BalanceIcon color="error" />;
    case 'date_inconsistency':
      return <DateIcon color="warning" />;
    case 'duplicate_entry':
      return <DuplicateIcon color="info" />;
    case 'suspicious_pattern':
      return <PatternIcon color="warning" />;
    case 'missing_data':
      return <ErrorIcon color="error" />;
    case 'incorrect_format':
      return <WarningIcon color="warning" />;
    case 'calculation_error':
      return <ErrorIcon color="error" />;
    default:
      return <InfoIcon color="info" />;
  }
};

const getSeverityColor = (confidenceScore) => {
  if (confidenceScore >= 0.9) return 'error';
  if (confidenceScore >= 0.7) return 'warning';
  if (confidenceScore >= 0.5) return 'info';
  return 'success';
};

const AnomalyDashboard = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fileMetadata, setFileMetadata] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [anomalyStats, setAnomalyStats] = useState({
    total: 0,
    byType: {},
    bySeverity: {
      high: 0,
      medium: 0,
      low: 0
    }
  });
  const [jobStatus, setJobStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);

  // Traiter les anomalies pour les statistiques
  const processAnomalies = (anomalies) => {
    const stats = {
      total: anomalies.length,
      byType: {},
      bySeverity: {
        high: 0,
        medium: 0,
        low: 0
      }
    };
    
    anomalies.forEach(anomaly => {
      // Compter par type
      if (!stats.byType[anomaly.type]) {
        stats.byType[anomaly.type] = 0;
      }
      stats.byType[anomaly.type]++;
      
      // Compter par sévérité
      if (anomaly.confidence_score >= 0.8) {
        stats.bySeverity.high++;
      } else if (anomaly.confidence_score >= 0.5) {
        stats.bySeverity.medium++;
      } else {
        stats.bySeverity.low++;
      }
    });
    
    setAnomalyStats(stats);
  };
  
  // Démarrer une nouvelle analyse
  const startNewAnalysis = async () => {
    try {
      setLoading(true);
      
      // Lancer l'analyse
      const analysisResponse = await analysisService.startAnalysis(fileId);
      
      if (analysisResponse.error) {
        throw new Error(analysisResponse.message);
      }
      
      // Définir l'ID du job et commencer le polling
      setJobStatus(analysisResponse);
      
      // Mettre en place le polling pour suivre l'avancement
      const interval = setInterval(() => pollJobStatus(analysisResponse.job_id), 3000);
      setPollingInterval(interval);
      
    } catch (err) {
      console.error('Erreur lors du démarrage de l\'analyse:', err);
      setError(err.message || 'Erreur lors du démarrage de l\'analyse');
      setLoading(false);
    }
  };
  
  // Vérifier le statut du job régulièrement
  const pollJobStatus = async (jobId) => {
    try {
      const statusResponse = await analysisService.checkAnalysisStatus(jobId);
      
      if (statusResponse.error) {
        throw new Error(statusResponse.message);
      }
      
      setJobStatus(statusResponse);
      
      // Si le job est terminé, arrêter le polling et récupérer les résultats
      if (statusResponse.status === 'completed') {
        clearInterval(pollingInterval);
        setPollingInterval(null);
        
        // Récupérer les résultats
        const resultsResponse = await analysisService.getAnalysisResults(fileId);
        
        if (resultsResponse.error) {
          throw new Error(resultsResponse.message);
        }
        
        setAnomalies(resultsResponse.anomalies || []);
        processAnomalies(resultsResponse.anomalies || []);
        setLoading(false);
      }
      
      // Si le job a échoué, arrêter le polling et afficher une erreur
      if (statusResponse.status === 'failed') {
        clearInterval(pollingInterval);
        setPollingInterval(null);
        throw new Error(statusResponse.message || 'L\'analyse a échoué');
      }
      
    } catch (err) {
      console.error('Erreur lors du polling:', err);
      clearInterval(pollingInterval);
      setPollingInterval(null);
      setError(err.message || 'Erreur lors du suivi de l\'analyse');
      setLoading(false);
    }
  };

  // Charger les données initiales
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Récupérer les métadonnées du fichier
        const fileResponse = await analysisService.listFiles();
        if (fileResponse.error) {
          throw new Error(fileResponse.message);
        }
        
        const fileData = fileResponse.find(file => file.file_id === fileId);
        if (!fileData) {
          throw new Error(`Fichier avec l'ID ${fileId} introuvable`);
        }
        
        setFileMetadata(fileData);
        
        // Vérifier s'il y a déjà des résultats d'analyse
        const resultsResponse = await analysisService.getAnalysisResults(fileId);
        
        if (!resultsResponse.error) {
          // Résultats trouvés, mettre à jour l'état
          setAnomalies(resultsResponse.anomalies || []);
          processAnomalies(resultsResponse.anomalies || []);
        } else {
          // Pas de résultats, lancer une nouvelle analyse
          startNewAnalysis();
        }
      } catch (err) {
        console.error('Erreur lors du chargement des données:', err);
        setError(err.message || 'Erreur lors du chargement des données');
      } finally {
        setLoading(false);
      }
    };
  
    fetchData();
    
    // Nettoyer le polling à la sortie du composant
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileId]);
  
  // Préparer les données pour le graphique en camembert des types d'anomalies
  const prepareTypeChartData = () => {
    return Object.entries(anomalyStats.byType).map(([type, count]) => ({
      name: type.replace('_', ' '),
      value: count
    }));
  };
  
  // Formatter les étiquettes du camembert
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name }) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius * 1.1;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    
    return (
      <text 
        x={x} 
        y={y} 
        fill="#333" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize={12}
      >
        {`${name} (${(percent * 100).toFixed(0)}%)`}
      </text>
    );
  };
  
  // Si en chargement, afficher un indicateur
  if (loading && !jobStatus) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', flexDirection: 'column' }}>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 2 }}>Chargement des données...</Typography>
        </Box>
      </Container>
    );
  }
  
  // Si une tâche est en cours, afficher sa progression
  if (jobStatus && (jobStatus.status === 'pending' || jobStatus.status === 'processing')) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <AnalysisStatusCard 
          status={jobStatus} 
          fileMetadata={fileMetadata}
        />
      </Container>
    );
  }
  
  // Si une erreur s'est produite, afficher un message
  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle1">{error}</Typography>
        </Alert>
        <Button 
          variant="contained" 
          onClick={() => navigate('/files')}
        >
          Retour à la liste des fichiers
        </Button>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* En-tête du dashboard */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="h4" gutterBottom>
              Analyse des anomalies
            </Typography>
            <Typography variant="subtitle1">
              Fichier: {fileMetadata?.filename}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Uploadé le: {new Date(fileMetadata?.upload_timestamp).toLocaleString()}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Taille: {(fileMetadata?.size_bytes / (1024 * 1024)).toFixed(2)} Mo
            </Typography>
          </Grid>
          <Grid item xs={12} md={4} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/files')}
              sx={{ mr: 2 }}
            >
              Retour
            </Button>
            <Button 
              variant="contained" 
              onClick={startNewAnalysis}
              disabled={loading}
            >
              Relancer l'analyse
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      {/* Reste du contenu... */}
      {/* ...existing code... */}
    </Container>
  );
};

export default AnomalyDashboard;