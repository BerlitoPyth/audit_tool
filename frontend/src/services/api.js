import axios from 'axios';

// Configuration de l'API
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Configuration de base d'axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  // Important: Set to false when using wildcard CORS
  withCredentials: false,
});

// Intercepteurs pour le debugging avec plus de détails
api.interceptors.request.use(request => {
  console.log('Starting Request:', {
    url: request.url,
    method: request.method,
    headers: request.headers,
    data: request.data
  });
  return request;
}, error => {
  console.error('Request Error:', error);
  return Promise.reject(error);
});

api.interceptors.response.use(
  response => {
    console.log('Response:', {
      status: response.status,
      data: response.data,
      headers: response.headers
    });
    return response;
  },
  error => {
    console.error('API Error:', {
      message: error.message,
      response: error.response ? {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        headers: error.response.headers
      } : null,
      request: error.request,
      config: error.config
    });
    
    // Format d'erreur standardisé pour l'UI
    const formattedError = {
      message: error.response?.data?.message || error.message || "Une erreur s'est produite",
      status: error.response?.status || 500,
      details: error.response?.data?.details || {},
      isAxiosError: true
    };
    
    return Promise.reject(formattedError);
  }
);

export const analysisService = {
  uploadFile: async (file, description) => {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/analysis/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        // Override withCredentials for upload
        withCredentials: false,
      });
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  },

  startAnalysis: async (fileId, options = {}) => {
    const response = await api.post('/analysis/start', {
      file_id: fileId,
      options,
    });
    return response.data;
  },

  getAnalysisResults: async (fileId) => {
    const response = await api.get(`/analysis/results/${fileId}`);
    return response.data;
  },

  listFiles: async () => {
    const response = await api.get('/analysis/files');
    return response.data;
  },
};

export const reportService = {
  generateReport: async (fileId, reportType, options = {}) => {
    const response = await api.post('/reports/generate', {
      file_id: fileId,
      report_type: reportType,
      options,
    });
    return response.data;
  },

  listReports: async (fileId = null) => {
    const params = fileId ? { file_id: fileId } : {};
    const response = await api.get('/reports/list', { params });
    return response.data;
  },
};

export default api;