// Configuration
const API_URL = 'http://127.0.0.1:8000/api/v1';
let currentFileId = null;
let currentJobId = null;
let statusCheckTimer = null;  // Pour stocker la référence au timer
let statusCheckAttempts = 0;  // Compteur de tentatives
const MAX_STATUS_CHECK_ATTEMPTS = 120;  // Limite de 2 minutes (à 1 requête/seconde)

// Éléments DOM
const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('file-input');
const descriptionInput = document.getElementById('description');
const uploadSection = document.getElementById('upload-section');
const analysisSection = document.getElementById('analysis-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const fileInfo = document.getElementById('file-info');
const analyzeBtn = document.getElementById('analyze-btn');
const progressBar = document.getElementById('analysis-progress');
const statusMessage = document.getElementById('status-message');
const resultSummary = document.getElementById('result-summary');
const anomaliesList = document.getElementById('anomalies-list');
const filesTable = document.getElementById('files-table');
const downloadReportBtn = document.getElementById('download-report-btn');

// Au chargement de la page
document.addEventListener('DOMContentLoaded', async () => {
    // Charger les fichiers récents
    await loadRecentFiles();
});

// Gérer l'upload de fichier
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!fileInput.files[0]) {
        alert('Veuillez sélectionner un fichier');
        return;
    }
    
    // Désactiver le bouton pour éviter les soumissions multiples
    const submitButton = document.getElementById('upload-btn');
    submitButton.disabled = true;
    submitButton.innerHTML = 'Upload en cours...';
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    if (descriptionInput.value) {
        formData.append('description', descriptionInput.value);
    }
    
    try {
        const response = await fetch(`${API_URL}/analysis/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors de l'upload: ${response.status}`);
        }
        
        const data = await response.json();
        currentFileId = data.file_id;
        
        // Afficher les informations du fichier
        fileInfo.textContent = `Fichier: ${data.filename} (${formatBytes(data.size_bytes)})`;
        
        // Passer à l'étape d'analyse
        uploadSection.classList.add('d-none');
        analysisSection.classList.remove('d-none');
        
    } catch (error) {
        alert(`Erreur: ${error.message}`);
        console.error(error);
    } finally {
        // Réactiver le bouton
        submitButton.disabled = false;
        submitButton.innerHTML = 'Uploader le fichier';
    }
});

// Lancer l'analyse
analyzeBtn.addEventListener('click', async () => {
    if (!currentFileId) return;
    
    // Désactiver le bouton pour éviter les clics multiples
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = 'Analyse en cours...';
    
    try {
        const response = await fetch(`${API_URL}/analysis/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                analysis_type: 'standard'
            })
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors du lancement de l'analyse: ${response.status}`);
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        // Afficher la section de progression
        analysisSection.classList.add('d-none');
        progressSection.classList.remove('d-none');
        
        // Démarrer la vérification périodique de l'état
        checkAnalysisStatus();
        
    } catch (error) {
        alert(`Erreur: ${error.message}`);
        console.error(error);
        
        // Réactiver le bouton en cas d'erreur
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'Détecter les anomalies';
    }
});

// Télécharger le rapport
downloadReportBtn.addEventListener('click', async () => {
    if (!currentFileId) return;
    
    try {
        const response = await fetch(`${API_URL}/reports/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                report_type: 'detailed',
                format: 'pdf'
            })
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la génération du rapport: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Rediriger vers l'URL de téléchargement
        window.open(`${API_URL}${data.url}`, '_blank');
        
    } catch (error) {
        alert(`Erreur: ${error.message}`);
        console.error(error);
    }
});

// Vérifier l'état de l'analyse
async function checkAnalysisStatus() {
    if (!currentJobId) return;
    
    // Limiter le nombre total de vérifications pour éviter les boucles infinies
    statusCheckAttempts++;
    if (statusCheckAttempts > MAX_STATUS_CHECK_ATTEMPTS) {
        console.warn(`Trop de vérifications (${statusCheckAttempts}). Arrêt des vérifications.`);
        statusMessage.textContent = "Vérification interrompue après trop de tentatives";
        return;  // Sortie définitive, pas de nouveau setTimeout
    }
    
    try {
        // Annuler le timer précédent s'il existe
        if (statusCheckTimer) {
            clearTimeout(statusCheckTimer);
            statusCheckTimer = null;
        }
        
        console.log(`Vérification du statut ${currentJobId} - tentative ${statusCheckAttempts}/${MAX_STATUS_CHECK_ATTEMPTS}`);
        
        const response = await fetch(`${API_URL}/analysis/status/${currentJobId}`);
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la vérification du statut: ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`Statut: ${data.status}, progression: ${data.progress}%`);
        
        // Mettre à jour la barre de progression
        progressBar.style.width = `${data.progress}%`;
        progressBar.setAttribute('aria-valuenow', data.progress);
        
        // Mettre à jour le message de statut
        if (data.status === 'pending') {
            statusMessage.textContent = 'En attente de traitement...';
            // Continuer la vérification avec un délai croissant pour réduire la charge
            const delay = Math.min(2000 + statusCheckAttempts * 100, 5000);
            statusCheckTimer = setTimeout(checkAnalysisStatus, delay);
            
        } else if (data.status === 'processing') {
            statusMessage.textContent = 'Analyse en cours...';
            // Continuer la vérification avec un délai croissant pour réduire la charge
            const delay = Math.min(1000 + statusCheckAttempts * 50, 3000);
            statusCheckTimer = setTimeout(checkAnalysisStatus, delay);
            
        } else if (data.status === 'completed') {
            statusMessage.textContent = 'Analyse terminée!';
            // Charger les résultats - pas de nouveau timer ici
            await loadAnalysisResults();
            // Réinitialiser le compteur de tentatives
            statusCheckAttempts = 0;
            
        } else if (data.status === 'failed') {
            statusMessage.textContent = `Erreur: ${data.error || 'Une erreur s\'est produite'}`;
            progressBar.classList.remove('bg-primary');
            progressBar.classList.add('bg-danger');
            // Réinitialiser le compteur de tentatives
            statusCheckAttempts = 0;
            
            // Afficher un bouton pour réessayer
            const retryButton = document.createElement('button');
            retryButton.className = 'btn btn-warning mt-3';
            retryButton.textContent = 'Réessayer';
            retryButton.onclick = () => {
                // Revenir à l'écran d'analyse
                progressSection.classList.add('d-none');
                analysisSection.classList.remove('d-none');
                // Réactiver le bouton d'analyse
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = 'Détecter les anomalies';
            };
            progressSection.appendChild(retryButton);
        }
        
    } catch (error) {
        console.error(`Erreur lors de la vérification du statut: ${error.message}`);
        statusMessage.textContent = `Erreur: ${error.message}`;
        
        // Après plusieurs échecs consécutifs, arrêter les vérifications
        const MAX_CONSECUTIVE_ERRORS = 3;
        
        if (window.statusCheckErrorCount === undefined) {
            window.statusCheckErrorCount = 0;
        }
        
        window.statusCheckErrorCount++;
        
        if (window.statusCheckErrorCount < MAX_CONSECUTIVE_ERRORS) {
            // Réessayer après un délai plus long
            statusCheckTimer = setTimeout(checkAnalysisStatus, 5000);
        } else {
            statusMessage.textContent += ' - Vérifications arrêtées après trop d\'erreurs';
            // Réinitialiser le compteur de tentatives
            statusCheckAttempts = 0;
            window.statusCheckErrorCount = 0;
        }
    }
}

// Charger les résultats d'analyse
async function loadAnalysisResults() {
    if (!currentFileId) return;
    
    try {
        const response = await fetch(`${API_URL}/analysis/results/${currentFileId}`);
        
        if (!response.ok) {
            throw new Error(`Erreur lors du chargement des résultats: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Afficher le résumé
        resultSummary.textContent = `${data.anomaly_count} anomalies détectées sur ${data.total_entries} écritures`;
        
        // Afficher les anomalies
        anomaliesList.innerHTML = '';
        if (data.anomalies && data.anomalies.length > 0) {
            data.anomalies.sort((a, b) => b.confidence_score - a.confidence_score);
            
            data.anomalies.forEach((anomaly, index) => {
                const confidenceClass = getConfidenceClass(anomaly.confidence_score);
                const confidenceText = getConfidenceText(anomaly.confidence_score);
                
                const anomalyItem = document.createElement('div');
                anomalyItem.className = `list-group-item anomaly-item ${confidenceClass}`;
                
                // Ligne principale
                anomalyItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1">${getAnomalyTypeText(anomaly.type)}</h5>
                            <p class="mb-1">${anomaly.description}</p>
                        </div>
                        <div>
                            <span class="badge bg-${getConfidenceColor(anomaly.confidence_score)} confidence-badge">${confidenceText}</span>
                            <button class="btn btn-sm btn-outline-secondary btn-details" data-index="${index}">Détails</button>
                        </div>
                    </div>
                    <div class="anomaly-details" id="details-${index}">
                        <p><strong>Lignes concernées:</strong> ${anomaly.line_numbers.join(', ')}</p>
                        <p><strong>Détecté le:</strong> ${new Date(anomaly.detected_at).toLocaleString()}</p>
                        ${getAdditionalInfo(anomaly.related_data)}
                    </div>
                `;
                
                anomaliesList.appendChild(anomalyItem);
            });
            
            // Ajouter les écouteurs pour les boutons de détails
            document.querySelectorAll('.btn-details').forEach(button => {
                button.addEventListener('click', () => {
                    const index = button.getAttribute('data-index');
                    const details = document.getElementById(`details-${index}`);
                    if (details.style.display === 'block') {
                        details.style.display = 'none';
                        button.textContent = 'Détails';
                    } else {
                        details.style.display = 'block';
                        button.textContent = 'Masquer';
                    }
                });
            });
        } else {
            anomaliesList.innerHTML = '<div class="alert alert-success">Aucune anomalie détectée!</div>';
        }
        
        // Passer à la section des résultats
        progressSection.classList.add('d-none');
        resultsSection.classList.remove('d-none');
        
        // Mettre à jour la liste des fichiers récents
        await loadRecentFiles();
        
    } catch (error) {
        statusMessage.textContent = `Erreur: ${error.message}`;
        console.error(error);
    }
}

// Charger la liste des fichiers récents
async function loadRecentFiles() {
    try {
        const response = await fetch(`${API_URL}/analysis/files`);
        
        if (!response.ok) {
            throw new Error(`Erreur lors du chargement des fichiers: ${response.status}`);
        }
        
        const files = await response.json();
        
        filesTable.innerHTML = '';
        if (files && files.length > 0) {
            files.forEach(file => {
                const row = document.createElement('tr');
                
                row.innerHTML = `
                    <td>${file.filename}</td>
                    <td>${new Date(file.upload_timestamp).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-results-btn" data-file-id="${file.file_id}">
                            Voir résultats
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-danger delete-file-btn" data-file-id="${file.file_id}">
                            Supprimer
                        </button>
                    </td>
                `;
                
                filesTable.appendChild(row);
            });
            
            // Ajouter les écouteurs pour les boutons d'action
            document.querySelectorAll('.view-results-btn').forEach(button => {
                button.addEventListener('click', () => {
                    const fileId = button.getAttribute('data-file-id');
                    viewFileResults(fileId);
                });
            });
            
            document.querySelectorAll('.delete-file-btn').forEach(button => {
                button.addEventListener('click', () => {
                    const fileId = button.getAttribute('data-file-id');
                    deleteFile(fileId);
                });
            });
        } else {
            filesTable.innerHTML = '<tr><td colspan="4" class="text-center">Aucun fichier analysé récemment</td></tr>';
        }
        
    } catch (error) {
        console.error(`Erreur lors du chargement des fichiers récents: ${error.message}`);
    }
}

// Voir les résultats d'un fichier
async function viewFileResults(fileId) {
    resetAnalysisState();  // Réinitialiser l'état avant de changer de vue
    currentFileId = fileId;
    
    // Réinitialiser l'interface
    uploadSection.classList.add('d-none');
    analysisSection.classList.add('d-none');
    progressSection.classList.add('d-none');
    resultsSection.classList.add('d-none');
    
    // Charger les résultats
    await loadAnalysisResults();
}

// Supprimer un fichier
async function deleteFile(fileId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce fichier et ses analyses?')) return;
    
    try {
        const response = await fetch(`${API_URL}/analysis/files/${fileId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Erreur lors de la suppression: ${response.status}`);
        }
        
        // Rafraîchir la liste des fichiers
        await loadRecentFiles();
        
        // Si le fichier courant est supprimé, réinitialiser l'interface
        if (fileId === currentFileId) {
            resetAnalysisState();
            currentFileId = null;
            currentJobId = null;
            uploadSection.classList.remove('d-none');
            analysisSection.classList.add('d-none');
            progressSection.classList.add('d-none');
            resultsSection.classList.add('d-none');
        }
        
    } catch (error) {
        alert(`Erreur lors de la suppression: ${error.message}`);
        console.error(error);
    }
}

// Fonctions utilitaires

// Formater les octets en taille lisible
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Obtenir le texte pour un type d'anomalie
function getAnomalyTypeText(type) {
    const typeMap = {
        'duplicate_entry': 'Doublon potentiel',
        'suspicious_pattern': 'Montant suspect',
        'missing_data': 'Données manquantes',
        'date_inconsistency': 'Incohérence de date',
        'balance_mismatch': 'Déséquilibre comptable',
        'unusual_account_activity': 'Activité inhabituelle',
        'other': 'Autre anomalie'
    };
    
    return typeMap[type] || type;
}

// Obtenir la classe CSS selon le niveau de confiance
function getConfidenceClass(score) {
    if (score >= 0.8) return 'anomaly-high';
    if (score >= 0.5) return 'anomaly-medium';
    return 'anomaly-low';
}

// Obtenir la couleur selon le niveau de confiance
function getConfidenceColor(score) {
    if (score >= 0.8) return 'danger';
    if (score >= 0.5) return 'warning';
    return 'info';
}

// Obtenir le texte selon le niveau de confiance
function getConfidenceText(score) {
    const percentage = Math.round(score * 100);
    if (score >= 0.8) return `Haute (${percentage}%)`;
    if (score >= 0.5) return `Moyenne (${percentage}%)`;
    return `Faible (${percentage}%)`;
}

// Obtenir les informations additionnelles
function getAdditionalInfo(data) {
    if (!data || Object.keys(data).length === 0) return '';
    
    let html = '<div class="mt-2"><strong>Informations supplémentaires:</strong><ul>';
    
    for (const [key, value] of Object.entries(data)) {
        if (typeof value === 'object' && value !== null) {
            html += `<li>${key}: ${JSON.stringify(value)}</li>`;
        } else {
            html += `<li>${key}: ${value}</li>`;
        }
    }
    
    html += '</ul></div>';
    return html;
}

// Reset function to clean up timers and counters when changing views
function resetAnalysisState() {
    // Clear any pending timers
    if (statusCheckTimer) {
        clearTimeout(statusCheckTimer);
        statusCheckTimer = null;
    }
    
    // Reset counters
    statusCheckAttempts = 0;
    if (window.statusCheckErrorCount !== undefined) {
        window.statusCheckErrorCount = 0;
    }
    
    // Reset UI elements if needed
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressBar.classList.remove('bg-danger');
        progressBar.classList.add('bg-primary');
    }
    
    if (statusMessage) {
        statusMessage.textContent = 'Initialisation de l\'analyse...';
    }
}
