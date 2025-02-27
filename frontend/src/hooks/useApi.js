import { useState, useCallback } from 'react';
import { useAppContext } from '../context/AppContext';

export const useApi = () => {
  const { setLoading, setError, showNotification } = useAppContext();
  const [data, setData] = useState(null);

  const execute = useCallback(async (apiCall, options = {}) => {
    const {
      showLoader = true,
      showError = true,
      showSuccess = false,
      successMessage = 'Opération réussie'
    } = options;

    try {
      if (showLoader) setLoading(true);
      const result = await apiCall();
      setData(result);
      
      if (showSuccess) {
        showNotification(successMessage, 'success');
      }
      
      return result;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      
      if (showError) {
        setError(errorMessage);
        showNotification(errorMessage, 'error');
      }
      
      throw err;
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [setLoading, setError, showNotification]);

  return { data, execute };
};
