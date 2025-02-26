import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Container, Paper, Typography, Box, Button, Divider,
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, TablePagination, IconButton, Chip, CircularProgress,
  Alert, AlertTitle, Dialog, DialogActions, DialogContent,
  DialogContentText, DialogTitle, TextField
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  BarChart as AnalysisIcon,
  Description as FileIcon,
  CloudDownload as DownloadIcon
} from '@mui/icons-material';
import { analysisService } from '../services/api';

/**
 * Page qui affiche la liste des fichiers uploadés avec possibilité de lancer des analyses
 */
const FileList = () => {
  const navigate = useNavigate();
  
  // États pour la liste de fichiers et la pagination
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // États pour les filtres et la recherche
  const [searchTerm, setSearchTerm] = useState('');
  
  // États pour la confirmation de suppression
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  
  // Charger les fichiers au chargement de la page
  useEffect(() => {
    fetchFiles();
  }, []);
  
  // Filtrer les fichiers en fonction du terme de recherche
  const filteredFiles = files.filter(file => 
    file.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  // Récupérer la liste des fichiers depuis l'API
  const fetchFiles = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await analysisService.listFiles();
      
      if (response.error) {
        throw new Error(response.message || 'Erreur lors de la récupération des fichiers');
      }
      
      setFiles(response);
    } catch (err) {
      console.error('Erreur lors du chargement des fichiers:', err);
      setError(err.message || 'Une erreur s\'est produite lors du chargement des fichiers');
    } finally {
      setLoading(false);
    }
  };
  
  // Gérer le changement de page
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };
  
  // Gérer le changement de nombre de lignes par page
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  // Ouvrir la boîte de dialogue de confirmation de suppression
  const handleOpenDeleteDialog = (file) => {
    setFileToDelete(file);
    setDeleteDialogOpen(true);
  };
  
  // Fermer la boîte de dialogue de confirmation
  const handleCloseDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setFileToDelete(null);
  };
  
  // Supprimer un fichier
  const handleDeleteFile = async () => {
    if (!fileToDelete) return;
    
    try {
      setLoading(true);
      
      const response = await analysisService.deleteFile(fileToDelete.file_id);
      
      if (response.error) {
        throw new Error(response.message || 'Erreur lors de la suppression du fichier');
      }
      
      // Recharger la liste des fichiers
      await fetchFiles();
      
      // Fermer la boîte de dialogue
      handleCloseDeleteDialog();
    } catch (err) {
      console.error('Erreur lors de la suppression:', err);
      setError(err.message || 'Une erreur s\'est produite lors de la suppression du fichier');
      handleCloseDeleteDialog();
    } finally {
      setLoading(false);
    }
  };
  
  // Naviguer vers la page d'analyse d'un fichier
  const handleViewAnalysis = (fileId) => {
    navigate(`/analysis/${fileId}`);
  };
  
  // Naviguer vers la page d'upload
  const handleGoToUpload = () => {
    navigate('/upload');
  };
  
  // Si chargement initial, afficher un spinner
  if (loading && files.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">
            Fichiers FEC
          </Typography>
          
          <Box>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchFiles}
              disabled={loading}
              sx={{ mr: 2 }}
            >
              Actualiser
            </Button>
            
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={handleGoToUpload}
            >
              Nouveau fichier
            </Button>
          </Box>
        </Box>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            <AlertTitle>Erreur</AlertTitle>
            {error}
          </Alert>
        )}
        
        <Box sx={{ mb: 3 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Rechercher un fichier..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />
            }}
            size="small"
          />
        </Box>
        
        <Divider sx={{ mb: 3 }} />
        
        {filteredFiles.length > 0 ? (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Nom du fichier</TableCell>
                    <TableCell>Date d'upload</TableCell>
                    <TableCell>Taille</TableCell>
                    <TableCell>Statut</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredFiles
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((file) => (
                      <TableRow key={file.file_id}>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <FileIcon color="primary" sx={{ mr: 1 }} />
                            <Typography variant="body2">
                              {file.filename}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          {new Date(file.upload_timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {(file.size_bytes / (1024 * 1024)).toFixed(2)} Mo
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={file.status || "Uploadé"} 
                            color={file.status === 'analyzed' ? 'success' : 'default'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <IconButton 
                            color="primary" 
                            onClick={() => handleViewAnalysis(file.file_id)}
                            title="Voir l'analyse"
                          >
                            <AnalysisIcon />
                          </IconButton>
                          <IconButton 
                            color="secondary" 
                            title="Télécharger"
                            disabled
                          >
                            <DownloadIcon />
                          </IconButton>
                          <IconButton 
                            color="error" 
                            onClick={() => handleOpenDeleteDialog(file)}
                            title="Supprimer"
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
            
            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={filteredFiles.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              labelRowsPerPage="Lignes par page:"
              labelDisplayedRows={({ from, to, count }) => `${from}-${to} sur ${count}`}
            />
          </>
        ) : (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            {searchTerm ? (
              <Typography variant="body1">
                Aucun fichier ne correspond à votre recherche.
              </Typography>
            ) : (
              <>
                <Typography variant="h6" gutterBottom>
                  Aucun fichier disponible
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  Commencez par uploader un fichier FEC pour l'analyser.
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<AddIcon />}
                  onClick={handleGoToUpload}
                >
                  Uploader un fichier
                </Button>
              </>
            )}
          </Box>
        )}
      </Paper>
      
      {/* Boîte de dialogue de confirmation de suppression */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleCloseDeleteDialog}
      >
        <DialogTitle>Confirmer la suppression</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Êtes-vous sûr de vouloir supprimer le fichier "{fileToDelete?.filename}" ? 
            Cette action est irréversible et supprimera toutes les analyses associées.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteDialog} color="primary">
            Annuler
          </Button>
          <Button onClick={handleDeleteFile} color="error" variant="contained">
            Supprimer
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default FileList;