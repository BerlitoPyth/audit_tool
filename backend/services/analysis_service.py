import logging
import time
import os
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from functools import lru_cache

from backend.core.config import get_settings
from backend.models.schemas import (
    Anomaly, AnomalyResponse, AnalysisJobStatus, AnalysisStatus, FileUploadResponse
)
from backend.models.anomaly_detector import AnomalyDetector, get_anomaly_detector
from backend.utils.file_handling import read_fec_file, delete_file

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    """Service pour gérer les analyses de fichiers FEC"""
    
    def __init__(self, anomaly_detector: AnomalyDetector):
        self.anomaly_detector = anomaly_detector
        self.files_dir = os.path.join(settings.DATA_DIR, "files")
        self.jobs_dir = os.path.join(settings.DATA_DIR, "jobs")
        self.results_dir = os.path.join(settings.DATA_DIR, "results")
        
        # Création des répertoires nécessaires
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.jobs_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Pour gérer les jobs en cours
        self._running_jobs = {}
        
    async def register_file(
        self, 
        file_id: str, 
        filename: str, 
        file_path: str, 
        file_size: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enregistre les métadonnées d'un fichier uploadé"""
        file_data = {
            "file_id": file_id,
            "filename": filename,
            "original_path": file_path,
            "size_bytes": file_size,
            "upload_timestamp": datetime.now().isoformat(),
            "description": description,
            "status": "uploaded"
        }
        
        # Sauvegarde des métadonnées
        file_metadata_path = os.path.join(self.files_dir, f"{file_id}.json")
        with open(file_metadata_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)
        
        return file_data
    
    async def file_exists(self, file_id: str) -> bool:
        """Vérifie si un fichier existe"""
        file_metadata_path = os.path.join(self.files_dir, f"{file_id}.json")
        return os.path.exists(file_metadata_path)
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les métadonnées d'un fichier"""
        if not await self.file_exists(file_id):
            return None
            
        file_metadata_path = os.path.join(self.files_dir, f"{file_id}.json")
        with open(file_metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    async def create_analysis_job(
        self, 
        file_id: str, 
        analysis_type: str = "standard",
        options: Optional[Dict[str, Any]] = None
    ) -> AnalysisJobStatus:
        """Crée une nouvelle tâche d'analyse"""
        job_id = str(uuid.uuid4())
        
        # Obtenir les métadonnées du fichier
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata:
            raise ValueError(f"Fichier avec l'ID {file_id} introuvable")
        
        # Création du statut initial de la tâche
        job_status = AnalysisJobStatus(
            job_id=job_id,
            file_id=file_id,
            status=AnalysisStatus.PENDING,
            progress=0.0,
            message="Initialisation de l'analyse",
            started_at=datetime.now(),
            completed_at=None,
            result_url=None
        )
        
        # Sauvegarde du statut initial
        job_status_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        with open(job_status_path, "w", encoding="utf-8") as f:
            json.dump(job_status.dict(), f, ensure_ascii=False, indent=2)
        
        return job_status
    
    async def update_job_status(
        self,
        job_id: str,
        status: Optional[AnalysisStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        result_url: Optional[str] = None
    ) -> AnalysisJobStatus:
        """Met à jour le statut d'une tâche d'analyse"""
        # Charger le statut actuel
        job_status_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        with open(job_status_path, "r", encoding="utf-8") as f:
            current_status_dict = json.load(f)
        
        # Convertir en objet AnalysisJobStatus
        current_status = AnalysisJobStatus(**current_status_dict)
        
        # Mettre à jour les champs si fournis
        if status is not None:
            current_status.status = status
        if progress is not None:
            current_status.progress = progress
        if message is not None:
            current_status.message = message
        if completed_at is not None:
            current_status.completed_at = completed_at
        if result_url is not None:
            current_status.result_url = result_url
        
        # Sauvegarder les modifications
        with open(job_status_path, "w", encoding="utf-8") as f:
            json.dump(current_status.dict(), f, ensure_ascii=False, indent=2)
        
        return current_status
    
    async def get_analysis_job_status(self, job_id: str) -> Optional[AnalysisJobStatus]:
        """Récupère le statut d'une tâche d'analyse"""
        job_status_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        if not os.path.exists(job_status_path):
            return None
        
        with open(job_status_path, "r", encoding="utf-8") as f:
            job_status_dict = json.load(f)
        
        return AnalysisJobStatus(**job_status_dict)
    
    async def run_analysis_job(self, job_id: str) -> None:
        """Exécute une analyse en arrière-plan"""
        try:
            # Récupérer le statut initial
            job_status = await self.get_analysis_job_status(job_id)
            if not job_status:
                logger.error(f"Tâche d'analyse {job_id} introuvable")
                return
            
            # Récupérer les métadonnées du fichier
            file_metadata = await self.get_file_metadata(job_status.file_id)
            if not file_metadata:
                logger.error(f"Fichier {job_status.file_id} introuvable")
                await self.update_job_status(
                    job_id=job_id,
                    status=AnalysisStatus.FAILED,
                    message="Fichier introuvable",
                    completed_at=datetime.now()
                )
                return
            
            # Marquer comme en cours de traitement
            await self.update_job_status(
                job_id=job_id,
                status=AnalysisStatus.PROCESSING,
                progress=0.1,
                message="Chargement du fichier FEC"
            )
            
            # Enregistrer le job en cours
            self._running_jobs[job_id] = {
                "start_time": time.time(),
                "file_id": job_status.file_id
            }
            
            # Charger le fichier FEC
            file_path = file_metadata.get("original_path")
            if not os.path.exists(file_path):
                logger.error(f"Fichier physique {file_path} introuvable")
                await self.update_job_status(
                    job_id=job_id,
                    status=AnalysisStatus.FAILED,
                    message="Fichier physique introuvable",
                    completed_at=datetime.now()
                )
                return
            
            # Pour les fichiers volumineux, utiliser un traitement par lots
            await self.update_job_status(
                job_id=job_id,
                progress=0.2,
                message="Prétraitement des données"
            )
            
            # Simuler le traitement par lots pour les fichiers volumineux
            fec_entries = await read_fec_file(file_path)
            
            # Progression de l'analyse
            await self.update_job_status(
                job_id=job_id,
                progress=0.4,
                message="Analyse en cours"
            )
            
            # Traitement par le détecteur d'anomalies
            start_time = time.time()
            anomalies = await self.anomaly_detector.detect_anomalies(fec_entries)
            analysis_duration_ms = (time.time() - start_time) * 1000
            
            # Création du résultat
            result = AnomalyResponse(
                anomalies=anomalies,
                total_count=len(anomalies),
                file_id=job_status.file_id,
                analysis_duration_ms=analysis_duration_ms
            )
            
            # Sauvegarde des résultats
            result_path = os.path.join(self.results_dir, f"{job_status.file_id}.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result.dict(), f, ensure_ascii=False, indent=2)
            
            # Mise à jour du statut comme terminé
            result_url = f"/api/v1/analysis/results/{job_status.file_id}"
            await self.update_job_status(
                job_id=job_id,
                status=AnalysisStatus.COMPLETED,
                progress=1.0,
                message=f"Analyse terminée, {len(anomalies)} anomalies détectées",
                completed_at=datetime.now(),
                result_url=result_url
            )
            
            logger.info(f"Analyse {job_id} terminée avec succès: {len(anomalies)} anomalies détectées")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse {job_id}: {str(e)}", exc_info=e)
            try:
                await self.update_job_status(
                    job_id=job_id,
                    status=AnalysisStatus.FAILED,
                    message=f"Erreur: {str(e)}",
                    completed_at=datetime.now()
                )
            except Exception as update_error:
                logger.error(f"Erreur lors de la mise à jour du statut pour {job_id}: {str(update_error)}")
        finally:
            # Supprimer des jobs en cours
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
    
    async def get_analysis_results(self, file_id: str) -> Optional[AnomalyResponse]:
        """Récupère les résultats d'une analyse"""
        result_path = os.path.join(self.results_dir, f"{file_id}.json")
        if not os.path.exists(result_path):
            return None
        
        with open(result_path, "r", encoding="utf-8") as f:
            result_dict = json.load(f)
        
        return AnomalyResponse(**result_dict)
    
    async def list_files(self, page: int = 1, page_size: int = 20) -> List[FileUploadResponse]:
        """Liste les fichiers uploadés avec pagination"""
        # Récupérer tous les fichiers de métadonnées
        files = []
        for filename in os.listdir(self.files_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.files_dir, filename), "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    # Convertir le timestamp en datetime
                    upload_timestamp = datetime.fromisoformat(file_data["upload_timestamp"])
                    
                    files.append(FileUploadResponse(
                        file_id=file_data["file_id"],
                        filename=file_data["filename"],
                        size_bytes=file_data["size_bytes"],
                        upload_timestamp=upload_timestamp,
                        content_type="application/fec",  # Supposant un type de contenu FEC
                        status=file_data.get("status", "uploaded"),
                        message=file_data.get("description")
                    ))
        
        # Trier par date d'upload (plus récent en premier)
        files.sort(key=lambda x: x.upload_timestamp, reverse=True)
        
        # Calculer l'offset et retourner la page demandée
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return files[start_idx:end_idx]
    
    async def delete_file(self, file_id: str) -> bool:
        """Supprime un fichier et ses analyses associées"""
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata:
            return False
        
        # Supprimer le fichier physique
        file_path = file_metadata.get("original_path")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Supprimer les métadonnées
        metadata_path = os.path.join(self.files_dir, f"{file_id}.json")
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        # Supprimer les résultats d'analyse
        results_path = os.path.join(self.results_dir, f"{file_id}.json")
        if os.path.exists(results_path):
            os.remove(results_path)
        
        # Supprimer les jobs associés (si nécessaire)
        for filename in os.listdir(self.jobs_dir):
            if filename.endswith(".json"):
                job_path = os.path.join(self.jobs_dir, filename)
                with open(job_path, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    if job_data.get("file_id") == file_id:
                        os.remove(job_path)
        
        return True


@lru_cache()
def get_analysis_service() -> AnalysisService:
    """Singleton pour récupérer le service d'analyse"""
    return AnalysisService(get_anomaly_detector())