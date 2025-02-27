"""Endpoints de vérification de santé de l'API"""
import os
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.training.model_registry import get_model_registry
from backend.models.trained_detector import get_trained_detector
from backend.utils.os_utils import get_disk_usage

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

class HealthCheckResponse(BaseModel):
    """Modèle de réponse pour le healthcheck"""
    status: str
    timestamp: str
    version: str
    environment: str
    model_info: Dict[str, Any]
    disk_usage: Dict[str, Any]

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Vérifie l'état de santé de l'application
    """
    try:
        # Vérifier le modèle actif
        registry = get_model_registry()
        active_model = registry.get_active_model_info()
        
        # Utiliser notre fonction cross-platform pour obtenir l'utilisation du disque
        disk_stats = get_disk_usage(settings.DATA_DIR)
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version=settings.VERSION,
            environment=settings.ENV,
            model_info={
                "has_active_model": active_model is not None,
                "active_version": active_model["version"] if active_model else None,
                "model_count": len(registry.list_models())
            },
            disk_usage=disk_stats
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du healthcheck: {str(e)}", exc_info=e)
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version=settings.VERSION,
            environment=settings.ENV,
            model_info={
                "error": str(e)
            },
            disk_usage={}
        )

@router.get("/ready")
async def readiness_check():
    """
    Vérifie si l'application est prête à recevoir du trafic
    """
    # Vérifier les dépendances critiques
    try:
        # Vérifier l'accès au système de fichiers
        os.listdir(settings.DATA_DIR)
        
        # Vérifier le chargement du modèle - renvoyer ready même si ML n'est pas chargé
        detector = get_trained_detector()
        model_status = "loaded" if detector._use_ml_models else "rules_only"
        
        return {"status": "ready", "model_status": model_status}
        
    except Exception as e:
        logger.error(f"L'application n'est pas prête: {str(e)}", exc_info=e)
        return {"status": "not_ready", "reason": str(e)}

@router.get("/live")
async def liveness_check():
    """
    Vérifie si l'application est vivante
    """
    return {"status": "alive"}
