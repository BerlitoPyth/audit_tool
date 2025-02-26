import axios from 'axios';

// Configurez ici votre URL de base pour l'API
const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Crée une instance d'axios avec des configurations par défaut
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 secondes pour les requêtes normales
});

// Instance d'axios spécifique pour les uploads de fichiers
const fileApi = axios.create({
  baseURL: BASE_URL,
  timeout: 600000, // 10 minutes pour les uploads de fichiers volumineux
});

// Gestion globale des erreurs
const handleApiError = (error) => {
  if (error.response) {
    // La requête a été faite et le serveur a répondu avec un code d'erreur
    console.error('Erreur API:', error.response.data);
    return {
      error: true,
      status: error.response.status,
      message: error.response.data.message || 'Une erreur est survenue',
      details: error.response.data.details || {},
    };
  } else if (error.request) {
    // La requête a été faite mais aucune réponse n'a été reçue
    console.error('Erreur réseau:', error.request);
    return {
      error: true,
      status: 0,
      message: 'Impossible de communiquer avec le serveur',
      details: { network: true },
    };
  } else {
    // Une erreur s'est produite lors de la configuration de la requête
    console.error('Erreur de configuration:', error.message);
    return {
      error: true,
      status: 0,
      message: 'Erreur de configuration de la requête',
      details: { message: error.message },
    };
  }
};

// Services API pour l'analyse
const analysisService = {
  // Upload d'un fichier FEC
  uploadFile: async (file, description = '') => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (description) {
        formData.append('description', description);
      }
      
      const response = await fileApi.post('/analysis/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          // Vous pouvez utiliser cette fonction pour suivre la progression
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          console.log(`Progression de l'upload: ${percentCompleted}%`);
        },
      });
      
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Démarrer une analyse
  startAnalysis: async (fileId, analysisType = 'standard', options = {}) => {
    try {
      const response = await api.post('/analysis/start', {
        file_id: fileId,
        analysis_type: analysisType,
        options: options,
      });
      
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Vérifier le statut d'une analyse
  checkAnalysisStatus: async (jobId) => {
    try {
      const response = await api.get(`/analysis/status/${jobId}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Récupérer les résultats d'une analyse
  getAnalysisResults: async (fileId) => {
    try {
      const response = await api.get(`/analysis/results/${fileId}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Lister les fichiers uploadés
  listFiles: async (page = 1, pageSize = 20) => {
    try {
      const response = await api.get('/analysis/files', {
        params: { page, page_size: pageSize },
      });
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Supprimer un fichier
  deleteFile: async (fileId) => {
    try {
      const response = await api.delete(`/analysis/files/${fileId}`);
      return { success: true };
    } catch (error) {
      return handleApiError(error);
    }
  },
};

// Services API pour les rapports
const reportService = {
  // Générer un rapport
  generateReport: async (fileId, reportType = 'anomaly_summary', options = {}) => {
    try {
      const response = await api.post('/reports/generate', {
        file_id: fileId,
        report_type: reportType,
        options: options,
      });
      
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Vérifier le statut d'un rapport
  checkReportStatus: async (jobId) => {
    try {
      const response = await api.get(`/reports/status/${jobId}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Récupérer un rapport
  getReport: async (reportId) => {
    try {
      const response = await api.get(`/reports/${reportId}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
};

// Services API pour la génération FEC
const fecGenerationService = {
  // Générer des données FEC
  generateFecData: async (params = {}) => {
    try {
      const response = await api.post('/fec/generate', params);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  // Télécharger un fichier FEC généré
  downloadGeneratedFec: async (fileId) => {
    try {
      const response = await fileApi.get(`/fec/download/${fileId}`, {
        responseType: 'blob',
      });
      
      // Créer un URL pour le téléchargement
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fec_${fileId}.csv`);
      document.body.appendChild(link);
      link.click();
      
      return { success: true };
    } catch (error) {
      return handleApiError(error);
    }
  },
};

export { api, fileApi, analysisService, reportService, fecGenerationService };