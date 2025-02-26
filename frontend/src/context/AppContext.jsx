import React, { createContext, useState, useContext, useEffect } from 'react';

// Création du contexte
const AppContext = createContext();

/**
 * Fournisseur du contexte de l'application
 * Gère les états globaux comme l'authentification, les préférences utilisateur, etc.
 */
export const AppContextProvider = ({ children }) => {
  // État de notification global
  const [notification, setNotification] = useState(null);
  
  // État des préférences utilisateur
  const [userPreferences, setUserPreferences] = useState(() => {
    // Charger les préférences depuis le localStorage si disponibles
    const savedPreferences = localStorage.getItem('userPreferences');
    return savedPreferences 
      ? JSON.parse(savedPreferences)
      : {
          darkMode: false,
          language: 'fr',
          dashboardLayout: 'default',
        };
  });

  // Sauvegarder les préférences utilisateur dans localStorage quand elles changent
  useEffect(() => {
    localStorage.setItem('userPreferences', JSON.stringify(userPreferences));
  }, [userPreferences]);

  // Fonction pour afficher une notification
  const showNotification = (message, severity = 'info', duration = 5000) => {
    setNotification({ message, severity, duration });
    
    // Auto-fermeture après duration
    if (duration > 0) {
      setTimeout(() => {
        setNotification(null);
      }, duration);
    }
  };

  // Fonction pour fermer la notification
  const closeNotification = () => {
    setNotification(null);
  };

  // Fonction pour mettre à jour les préférences utilisateur
  const updateUserPreferences = (newPreferences) => {
    setUserPreferences(prev => ({
      ...prev,
      ...newPreferences
    }));
  };

  // Retourner le contexte et les fonctions associées
  const contextValue = {
    notification,
    showNotification,
    closeNotification,
    userPreferences,
    updateUserPreferences,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Hook personnalisé pour utiliser le contexte
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext doit être utilisé dans un AppContextProvider');
  }
  return context;
};

export default AppContext;