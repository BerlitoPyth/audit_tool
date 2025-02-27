"""
Service pour l'analyse des fichiers FEC et la détection d'anomalies.
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import uuid
import time
from functools import lru_cache

from backend.models.schemas import (
    Anomaly, AnomalyResponse, AnalysisJobStatus, AnalysisType, 
    FileUploadResponse, PaginationParams, AnalysisStatus
)
from backend.models.anomaly_detector import AnomalyDetector, get_anomaly_detector
from backend.core.config import get_settings
from backend.core.errors import ResourceNotFoundError, FileProcessingError
from backend.utils.file_handling import read_file_content

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    """Service d'analyse des fichiers comptables"""
    
    def __init__(self, anomaly_detector: Optional[AnomalyDetector] = None):
        """
        Initialise le service d'analyse
        
        Args:
            anomaly_detector: Détecteur d'anomalies à utiliser (optionnel)
        """
        self.anomaly_detector = anomaly_detector or get_anomaly_detector()
        self.data_dir = settings.DATA_DIR
        
        # Répertoires spécifiques
        self.uploads_dir = os.path.join(self.data_dir, "uploads")
        self.results_dir = os.path.join(self.data_dir, "results")
        self.jobs_dir = os.path.join(self.data_dir, "jobs")
        
        # Créer les répertoires s'ils n'existent pas
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.jobs_dir, exist_ok=True)
        
        # Pour gérer les jobs en cours
        self._running_jobs = {}
    
    async def register_file(self, 
                    file_id: str, 
                    filename: str, 
                    file_path: str, 
                    file_size: int, 
                    description: Optional[str] = None) -> Dict[str, Any]:
        """
        Enregistre les métadonnées d'un fichier uploadé
        
        Args:
            file_id: Identifiant unique du fichier
            filename: Nom original du fichier
            file_path: Chemin d'accès au fichier
            file_size: Taille du fichier en octets
            description: Description optionnelle du fichier
        
        Returns:
            Dictionnaire des métadonnées du fichier
        """
        # Créer les métadonnées du fichier
        file_data = {
            "file_id": file_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "upload_timestamp": datetime.now().isoformat(),
            "description": description or "",
            "status": "uploaded",
            "analyses": []
        }
        
        # Enregistrer les métadonnées
        metadata_path = os.path.join(self.uploads_dir, f"{file_id}_meta.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Métadonnées du fichier {file_id} enregistrées")
        return file_data
    
    async def file_exists(self, file_id: str) -> bool:
        """
        Vérifie si un fichier existe
        
        Args:
            file_id: Identifiant du fichier
            
        Returns:
            True si le fichier existe, False sinon
        """
        metadata_path = os.path.join(self.uploads_dir, f"{file_id}_meta.json")
        return os.path.exists(metadata_path)
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les métadonnées d'un fichier
        
        Args:
            file_id: Identifiant du fichier
            
        Returns:
            Métadonnées du fichier ou None si introuvable
        """
        metadata_path = os.path.join(self.uploads_dir, f"{file_id}_meta.json")
        
        if not os.path.exists(metadata_path):
            return None
        
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    async def create_analysis_job(self, 
                          file_id: str, 
                          analysis_type: AnalysisType, 
                          options: Optional[Dict[str, Any]] = None) -> AnalysisJobStatus:
        """
        Crée une tâche d'analyse
        
        Args:
            file_id: Identifiant du fichier à analyser
            analysis_type: Type d'analyse à effectuer
            options: Options supplémentaires pour l'analyse
            
        Returns:
            Statut initial de la tâche
        """
        # Vérifier que le fichier existe
        if not await self.file_exists(file_id):
            raise ResourceNotFoundError("Fichier", file_id)
        
        # Créer un identifiant unique pour la tâche
        job_id = str(uuid.uuid4())
        
        # Créer les données de la tâche
        job_data = {
            "job_id": job_id,
            "file_id": file_id,
            "analysis_type": analysis_type.value,
            "options": options or {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result_path": None,
            "progress": 0
        }
        
        # Enregistrer les données de la tâche
        job_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Tâche d'analyse {job_id} créée pour le fichier {file_id}")
        
        return AnalysisJobStatus(
            job_id=job_id,
            file_id=file_id,
            status=AnalysisStatus.PENDING,
            progress=0,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            error=None,
            result_path=None
        )
    
    async def run_analysis_job(self, job_id: str) -> AnalysisJobStatus:
        """
        Exécute une tâche d'analyse
        
        Args:
            job_id: Identifiant de la tâche
            
        Returns:
            Statut final de la tâche
        """
        # Récupérer les données de la tâche
        job_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        
        if not os.path.exists(job_path):
            raise ResourceNotFoundError("Tâche d'analyse", job_id)
        
        with open(job_path, "r", encoding="utf-8") as f:
            job_data = json.load(f)
        
        # Mettre à jour le statut
        job_data["status"] = "processing"
        job_data["started_at"] = datetime.now().isoformat()
        
        # Sauvegarder l'état initial
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        try:
            # Récupérer les métadonnées du fichier
            file_id = job_data["file_id"]
            metadata = await self.get_file_metadata(file_id)
            
            if not metadata:
                raise ResourceNotFoundError("Fichier", file_id)
            
            file_path = metadata["file_path"]
            
            # Mettre à jour la progression
            job_data["progress"] = 10
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
            
            # Charger le contenu du fichier
            logger.info(f"Chargement du fichier {file_path}")
            entries = await read_file_content(file_path)
            
            # Mettre à jour la progression
            job_data["progress"] = 30
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
            
            # Détecter les anomalies
            logger.info(f"Détection d'anomalies sur {len(entries)} entrées")
            
            # Mettre à jour la progression
            job_data["progress"] = 50
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
            
            # Effectuer la détection
            detector = get_anomaly_detector()
            anomalies = await detector.detect_anomalies(entries)
            
            # Mettre à jour la progression
            job_data["progress"] = 80
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
            
            # Créer le résultat
            result = AnomalyResponse(
                file_id=file_id,
                filename=metadata["filename"],
                total_entries=len(entries),
                anomaly_count=len(anomalies),
                anomalies=anomalies,
                analysis_timestamp=datetime.now(),
                processing_time_ms=int((datetime.now() - datetime.fromisoformat(job_data["started_at"])).total_seconds() * 1000)
            )
            
            # Sauvegarder le résultat
            result_path = os.path.join(self.results_dir, f"{file_id}.json")
            with open(result_path, "w", encoding="utf-8") as f:
                # Correction ici: d'abord convertir en dict puis utiliser json.dump
                import json
                result_dict = result.model_dump()
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
            # Mettre à jour le statut de la tâche
            job_data["status"] = "completed"
            job_data["completed_at"] = datetime.now().isoformat()
            job_data["result_path"] = result_path
            job_data["progress"] = 100
            
            # Ajouter l'analyse aux métadonnées du fichier
            metadata["analyses"].append({
                "job_id": job_id,
                "analysis_type": job_data["analysis_type"],
                "timestamp": datetime.now().isoformat(),
                "anomaly_count": len(anomalies)
            })
            
            # Mettre à jour les métadonnées du fichier
            metadata_path = os.path.join(self.uploads_dir, f"{file_id}_meta.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Analyse {job_id} terminée: {len(anomalies)} anomalies détectées")
            
        except Exception as e:
            # En cas d'erreur, mettre à jour le statut
            job_data["status"] = "failed"
            job_data["error"] = str(e)
            logger.error(f"Erreur lors de l'analyse {job_id}: {str(e)}", exc_info=e)
        
        finally:
            # Sauvegarder l'état final
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        return await self.get_analysis_job_status(job_id)
    
    async def get_analysis_job_status(self, job_id: str) -> Optional[AnalysisJobStatus]:
        """
        Récupère le statut d'une tâche d'analyse
        
        Args:
            job_id: Identifiant de la tâche
            
        Returns:
            Statut de la tâche ou None si introuvable
        """
        job_path = os.path.join(self.jobs_dir, f"{job_id}.json")
        
        if not os.path.exists(job_path):
            return None
        
        with open(job_path, "r", encoding="utf-8") as f:
            job_data = json.load(f)
        
        # Convertir les chaînes ISO en objets datetime
        created_at = datetime.fromisoformat(job_data["created_at"])
        started_at = datetime.fromisoformat(job_data["started_at"]) if job_data["started_at"] else None  
        completed_at = datetime.fromisoformat(job_data["completed_at"]) if job_data["completed_at"] else None
        
        # Convertir le statut en AnalysisStatus
        status_map = {
            "pending": AnalysisStatus.PENDING,
            "processing": AnalysisStatus.PROCESSING,
            "completed": AnalysisStatus.COMPLETED,
            "failed": AnalysisStatus.FAILED
        }
        status = status_map.get(job_data["status"], AnalysisStatus.PENDING)
        
        return AnalysisJobStatus(
            job_id=job_data["job_id"],
            file_id=job_data["file_id"],
            status=status,
            progress=job_data["progress"],
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            error=job_data["error"],
            result_path=job_data["result_path"]
        )
    
    async def get_analysis_results(self, file_id: str) -> Optional[AnomalyResponse]:
        """
        Récupère les résultats d'analyse pour un fichier
        
        Args:
            file_id: Identifiant du fichier
            
        Returns:
            Résultats d'analyse ou None si introuvable
        """
        result_path = os.path.join(self.results_dir, f"{file_id}.json")
        
        if not os.path.exists(result_path):
            return None
        
        with open(result_path, "r", encoding="utf-8") as f:
            result_json = json.load(f)
        
        # Convertir le JSON en objet AnomalyResponse
        return AnomalyResponse(**result_json)
    
    async def list_files(self, page: int = 1, page_size: int = 20) -> List[FileUploadResponse]:
        """
        Liste les fichiers uploadés avec pagination
        
        Args:
            page: Numéro de page (commence à 1)
            page_size: Nombre d'éléments par page
            
        Returns:
            Liste des métadonnées des fichiers
        """
        # Récupérer les fichiers de métadonnées
        files = []
        for filename in os.listdir(self.uploads_dir):
            if filename.endswith("_meta.json"):
                file_path = os.path.join(self.uploads_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        
                        files.append(FileUploadResponse(
                            file_id=file_data["file_id"],
                            filename=file_data["filename"],
                            size_bytes=file_data["file_size"],
                            upload_timestamp=datetime.fromisoformat(file_data["upload_timestamp"]),
                            content_type="application/octet-stream",  # À améliorer si nécessaire
                            status=file_data["status"],
                            message=""
                        ))
                except Exception as e:
                    logger.error(f"Erreur lors de la lecture des métadonnées {file_path}: {str(e)}")
        
        # Trier par date d'upload (plus récent d'abord)
        files.sort(key=lambda x: x.upload_timestamp, reverse=True)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return files[start_idx:end_idx]
    
    async def delete_file(self, file_id: str) -> bool:
        """
        Supprime un fichier et ses analyses associées
        
        Args:
            file_id: Identifiant du fichier
            
        Returns:
            True si la suppression a réussi
        """
        # Vérifier que le fichier existe
        metadata_path = os.path.join(self.uploads_dir, f"{file_id}_meta.json")
        
        if not os.path.exists(metadata_path):
            raise ResourceNotFoundError("Fichier", file_id)
        
        # Récupérer les métadonnées
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Supprimer le fichier physique
        file_path = metadata.get("file_path")
        if file_path and os.path.exists(file_path):  # Correction ici: remplacé & par and
            os.remove(file_path)
        
        # Supprimer les métadonnées
        os.remove(metadata_path)
        
        # Supprimer les résultats d'analyse
        result_path = os.path.join(self.results_dir, f"{file_id}.json")
        if os.path.exists(result_path):
            os.remove(result_path)
        
        # Supprimer les tâches d'analyse associées
        for job_id in [job.get("job_id") for job in metadata.get("analyses", [])]:
            job_path = os.path.join(self.jobs_dir, f"{job_id}.json")
            if os.path.exists(job_path):
                os.remove(job_path)
        
        logger.info(f"Fichier {file_id} et données associées supprimés")
        return True


@lru_cache()
def get_analysis_service() -> AnalysisService:
    """
    Récupère l'instance unique du service d'analyse
    
    Returns:
        Instance du service d'analyse
    """
    return AnalysisService()

