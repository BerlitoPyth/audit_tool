from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from typing import List, Dict, Any, Optional
import logging
import sys  # Ajout de l'import manquant pour sys.executable
import os
import uuid
import subprocess
from pydantic import BaseModel, Field
from datetime import datetime

from backend.training.model_registry import get_model_registry, ModelRegistry
from backend.models.trained_detector import get_trained_detector, TrainedDetector
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class ModelMetrics(BaseModel):
    """Métriques d'un modèle de détection"""
    version: str
    created_at: datetime
    is_active: bool
    metrics: Dict[str, float] = {}
    metadata: Dict[str, Any] = {}


class ModelList(BaseModel):
    """Liste de modèles avec métadonnées"""
    models: List[ModelMetrics]
    active_version: Optional[str] = None


class ModelActivationRequest(BaseModel):
    """Requête pour activer un modèle"""
    version: str = Field(..., description="Version du modèle à activer")


class ModelActivationResponse(BaseModel):
    """Réponse à une activation de modèle"""
    success: bool
    message: str
    version: str


class TrainingRequest(BaseModel):
    """Requête pour lancer un entraînement de modèle"""
    num_sets: int = Field(default=10, ge=1, le=50, description="Nombre de jeux de données à générer")
    entries_per_set: int = Field(default=500, ge=100, le=5000, description="Nombre d'entrées par jeu")
    description: Optional[str] = Field(None, description="Description du modèle")
    activate: bool = Field(default=True, description="Activer le modèle après entraînement")


class TrainingResponse(BaseModel):
    """Réponse à une demande d'entraînement"""
    job_id: str
    status: str
    message: str


class TrainingStatusResponse(BaseModel):
    """Réponse à une demande de statut d'entraînement"""
    job_id: str
    status: str
    last_logs: str
    log_file: str
    progress: Optional[float] = None


@router.get("/list", response_model=ModelList)
async def list_models(
    registry: ModelRegistry = Depends(get_model_registry)
):
    """Liste tous les modèles de détection disponibles"""
    try:
        models = registry.list_models()
        active_version = None
        
        active_model = registry.get_active_model_info()
        if active_model:
            active_version = active_model["version"]
        
        # Convertir au format attendu
        model_metrics = []
        for model in models:
            metrics = ModelMetrics(
                version=model["version"],
                created_at=datetime.fromisoformat(model.get("created_at", datetime.now().isoformat())),
                is_active=model.get("is_active", False),
                metrics=model.get("metrics", {}),
                metadata=model.get("metadata", {})
            )
            model_metrics.append(metrics)
        
        return ModelList(
            models=model_metrics,
            active_version=active_version
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des modèles: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des modèles: {str(e)}"
        )


@router.post("/activate", response_model=ModelActivationResponse)
async def activate_model(
    request: ModelActivationRequest,
    registry: ModelRegistry = Depends(get_model_registry)
):
    """Active un modèle spécifique pour la détection"""
    try:
        # Vérifier que le modèle existe avant de tenter de l'activer
        model_files = registry.get_model_files(request.version)
        if not model_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Modèle version {request.version} non trouvé"
            )
            
        success = registry.set_active_model(request.version)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Échec de l'activation du modèle {request.version}"
            )
        
        # Recharger le détecteur avec le nouveau modèle
        detector = get_trained_detector()
        
        # Cette ligne force la réinitialisation du singleton
        import backend.models.trained_detector
        backend.models.trained_detector._detector = None
        
        return ModelActivationResponse(
            success=True,
            message=f"Modèle version {request.version} activé avec succès",
            version=request.version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'activation du modèle: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'activation du modèle: {str(e)}"
        )


@router.get("/active", response_model=ModelMetrics)
async def get_active_model(
    registry: ModelRegistry = Depends(get_model_registry)
):
    """Récupère les informations sur le modèle actif"""
    try:
        active_model = registry.get_active_model_info()
        
        if not active_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun modèle actif trouvé"
            )
        
        return ModelMetrics(
            version=active_model["version"],
            created_at=datetime.fromisoformat(active_model.get("created_at", datetime.now().isoformat())),
            is_active=True,
            metrics=active_model.get("metrics", {}),
            metadata=active_model.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du modèle actif: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du modèle actif: {str(e)}"
        )


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks
):
    """
    Lance un entraînement de modèle en arrière-plan.
    
    Cette fonction exécute un script d'entraînement qui peut prendre du temps à s'exécuter.
    Le traitement est donc fait de manière asynchrone en arrière-plan.
    
    Args:
        request: Paramètres pour l'entraînement du modèle
        background_tasks: Tâches à exécuter en arrière-plan
        
    Returns:
        Identifiant du job d'entraînement et statut initial
    """
    try:
        # Générer un ID unique pour le job
        job_id = str(uuid.uuid4())
        
        # Préparer le répertoire pour les logs
        log_dir = os.path.join(settings.DATA_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"train_{job_id}.log")
        status_file = os.path.join(log_dir, f"train_{job_id}_status.json")
        
        # Initialiser le fichier de statut
        import json
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({
                "job_id": job_id,
                "status": "initializing",
                "progress": 0,
                "message": "Initialisation de l'entraînement",
                "start_time": datetime.now().isoformat()
            }, f, indent=2)
        
        # Préparer la commande d'entraînement
        script_path = os.path.join(settings.PROJECT_ROOT, "scripts", "train_detector.py")
        cmd = [
            sys.executable,
            script_path,
            "--num-sets", str(request.num_sets),
            "--entries-per-set", str(request.entries_per_set),
            "--evaluate"
        ]
        
        if request.activate:
            cmd.append("--activate")
        
        if request.description:
            cmd.extend(["--description", request.description])
        
        # Fonction à exécuter en arrière-plan
        async def run_training():
            try:
                # Mise à jour du statut
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                
                status_data["status"] = "running"
                status_data["progress"] = 10
                status_data["message"] = "Entraînement en cours..."
                
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(status_data, f, indent=2)
                
                # Exécuter le processus d'entraînement
                with open(log_file, "w", encoding="utf-8") as f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    # Attendre la fin du processus
                    returncode = process.wait()
                
                # Mettre à jour le statut final
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                
                status_data["end_time"] = datetime.now().isoformat()
                
                if returncode == 0:
                    status_data["status"] = "completed"
                    status_data["message"] = "Entraînement terminé avec succès"
                    status_data["progress"] = 100
                else:
                    status_data["status"] = "failed"
                    status_data["message"] = f"Échec de l'entraînement (code {returncode})"
                    status_data["progress"] = 100
                
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(status_data, f, indent=2)
                
                logger.info(f"Entraînement terminé avec code de sortie {returncode}")
                
            except Exception as e:
                logger.error(f"Erreur pendant l'exécution de l'entraînement: {str(e)}", exc_info=True)
                
                # Mettre à jour le statut en cas d'erreur
                try:
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "job_id": job_id,
                            "status": "failed",
                            "progress": 100,
                            "message": f"Erreur: {str(e)}",
                            "end_time": datetime.now().isoformat()
                        }, f, indent=2)
                except:
                    pass
        
        # Lancer en arrière-plan
        background_tasks.add_task(run_training)
        
        return TrainingResponse(
            job_id=job_id,
            status="started",
            message="Entraînement du modèle démarré en arrière-plan"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'entraînement: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du démarrage de l'entraînement: {str(e)}"
        )


@router.get("/training-status/{job_id}", response_model=TrainingStatusResponse)
async def get_training_status(job_id: str):
    """
    Vérifie le statut d'un entraînement en cours
    
    Args:
        job_id: Identifiant du job d'entraînement
        
    Returns:
        État actuel de l'entraînement et dernières entrées du log
    """
    try:
        # Vérifier le fichier de statut
        status_file = os.path.join(settings.DATA_DIR, "logs", f"train_{job_id}_status.json")
        log_file = os.path.join(settings.DATA_DIR, "logs", f"train_{job_id}.log")
        
        if not os.path.exists(status_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucun entraînement trouvé avec l'ID {job_id}"
            )
        
        # Lire le statut
        import json
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        
        # Lire les dernières lignes du log
        last_lines = ""
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                # Lire les 20 dernières lignes
                lines = f.readlines()[-20:]
                last_lines = "".join(lines)
        
        return {
            "job_id": job_id,
            "status": status_data.get("status", "unknown"),
            "progress": status_data.get("progress", 0),
            "last_logs": last_lines,
            "log_file": log_file
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut de l'entraînement: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification du statut de l'entraînement: {str(e)}"
        )
