import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { AppContextProvider } from './context/AppContext';

// Pages
import Dashboard from './pages/Dashboard';
import FileList from './pages/FileList';
import FileUpload from './pages/FileUpload';
import AnomalyDashboard from './components/analysis/AnomalyDashboard';
import NotFound from './pages/NotFound';
import AppLayout from './components/layout/AppLayout';

// Définition du thème de l'application
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      'Arial',
      'sans-serif',
    ].join(','),
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          textTransform: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppContextProvider>
        <Router>
          <AppLayout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/files" element={<FileList />} />
              <Route path="/upload" element={<FileUpload />} />
              <Route path="/analysis/:fileId" element={<AnomalyDashboard />} />
              <Route path="/404" element={<NotFound />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </AppLayout>
        </Router>
      </AppContextProvider>
    </ThemeProvider>
  );
}

export default App;