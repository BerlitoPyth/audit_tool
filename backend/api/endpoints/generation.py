from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel, Field

from backend.services.generation_service import GenerationService, get_generation_service

logger = logging.getLogger(__name__)
router = APIRouter()

class GenerationRequest(BaseModel):
    """Modèle pour une requête de génération"""
    count: int = Field(default=1000, ge=10, le=10000, description="Nombre d'écritures à générer")
    anomaly_rate: float = Field(default=0.05, ge=0, le=1, description="Taux d'anomalies à introduire")
    start_date: Optional[str] = Field(None, description="Date de début (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Date de fin (YYYY-MM-DD)")
    company_name: Optional[str] = Field(None, description="Nom de l'entreprise")
    options: Optional[Dict[str, Any]] = Field(None, description="Options supplémentaires")

class GenerationResponse(BaseModel):
    """Modèle pour une réponse de génération"""
    generation_id: str
    count: int
    anomaly_count: int
    csv_path: str
    result_path: str
    duration_ms: float
    generated_at: str

@router.post("/generate", response_model=GenerationResponse)
async def generate_fec_data(
    request: GenerationRequest,
    generation_service: GenerationService = Depends(get_generation_service)
):
    """
    Génère des données FEC et les analyse pour détecter des anomalies
    """
    try:
        # Préparer les options
        options = request.options or {}
        if request.start_date:
            options["start_date"] = request.start_date
        if request.end_date:
            options["end_date"] = request.end_date
        if request.company_name:
            options["company_name"] = request.company_name
        
        # Générer et analyser
        result = await generation_service.generate_and_analyze(
            count=request.count,
            anomaly_rate=request.anomaly_rate,
            options=options
        )
        
        # Ne pas retourner le résultat d'analyse complet dans la réponse
        return {
            "generation_id": result["generation_id"],
            "count": result["count"],
            "anomaly_count": result["anomaly_count"],
            "csv_path": result["csv_path"],
            "result_path": result["result_path"],
            "duration_ms": result["duration_ms"],
            "generated_at": result["generated_at"]
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")

@router.get("/results/{generation_id}")
async def get_generation_results(
    generation_id: str,
    generation_service: GenerationService = Depends(get_generation_service)
):
    """
    Récupère les résultats d'une génération précédente
    """
    try:
        # Vérifier si le fichier de résultats existe
        import os
        from backend.core.config import get_settings
        settings = get_settings()
        
        result_path = os.path.join(settings.DATA_DIR, "generated", f"results_{generation_id}.json")
        
        if not os.path.exists(result_path):
            raise HTTPException(status_code=404, detail=f"Résultats non trouvés pour l'ID {generation_id}")
        
        # Charger et retourner les résultats
        import json
        with open(result_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        
        return results
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Erreur lors de la récupération des résultats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des résultats: {str(e)}")
