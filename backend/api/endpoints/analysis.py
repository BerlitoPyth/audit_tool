# Analysis endpoints
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import time
import uuid
import os
import logging
from datetime import datetime

from backend.core.config import get_settings
from backend.models.schemas import (
    AnomalyResponse, AnalysisRequest, AnalysisJobStatus, FileUploadResponse, PaginationParams
)
from backend.services.analysis_service import AnalysisService, get_analysis_service
from backend.utils.file_handling import save_upload_file, validate_file
from backend.core.errors import FileProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Endpoint pour uploader un fichier (FEC ou Excel).
    """
    start_time = time.time()
    
    # Validation de la taille du fichier
    content_length = file.size if hasattr(file, "size") else 0
    if content_length > settings.MAX_UPLOAD_SIZE:
        raise FileProcessingError(
            message=f"Taille du fichier ({content_length} octets) dépasse la limite maximale de {settings.MAX_UPLOAD_SIZE} octets",
            details={"max_size": settings.MAX_UPLOAD_SIZE, "received_size": content_length}
        )
    
    # Génération d'un ID unique pour le fichier
    file_id = str(uuid.uuid4())
    
    try:
        # Validation du format du fichier (FEC ou Excel)
        is_valid, validation_message = await validate_file(file)
        if not is_valid:
            raise FileProcessingError(
                message=f"Fichier invalide: {validation_message}",
                details={"reason": validation_message}
            )
        
        # Sauvegarde du fichier
        file_path = await save_upload_file(file, file_id, settings.DATA_DIR)
        file_size = os.path.getsize(file_path)
        
        # Enregistrement des métadonnées du fichier
        file_data = await analysis_service.register_file(
            file_id=file_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            description=description
        )
        
        logger.info(f"Fichier {file.filename} uploadé avec succès, ID: {file_id}, taille: {file_size} octets")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size_bytes=file_size,
            upload_timestamp=datetime.now(),
            content_type=file.content_type,
            status="uploaded",
            message="Fichier uploadé avec succès"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload du fichier {file.filename}: {str(e)}", exc_info=e)
        if isinstance(e, FileProcessingError):
            raise
        raise FileProcessingError(
            message=f"Erreur lors du traitement du fichier: {str(e)}",
            details={"error": str(e)}
        )


@router.post("/start", response_model=AnalysisJobStatus)
async def start_analysis(
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Démarre une tâche d'analyse asynchrone pour un fichier FEC.
    """
    try:
        # Vérification que le fichier existe
        if not await analysis_service.file_exists(analysis_request.file_id):
            raise ResourceNotFoundError("Fichier", analysis_request.file_id)
        
        # Création et démarrage de la tâche d'analyse
        job_status = await analysis_service.create_analysis_job(
            file_id=analysis_request.file_id,
            analysis_type=analysis_request.analysis_type,
            options=analysis_request.options
        )
        
        # Exécution de l'analyse en arrière-plan
        background_tasks.add_task(
            analysis_service.run_analysis_job,
            job_id=job_status.job_id
        )
        
        logger.info(f"Analyse démarrée pour le fichier {analysis_request.file_id}, job ID: {job_status.job_id}")
        
        return job_status
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'analyse: {str(e)}", exc_info=e)
        if isinstance(e, (ResourceNotFoundError, FileProcessingError)):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du démarrage de l'analyse: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=AnalysisJobStatus)
async def get_analysis_status(
    job_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Récupère le statut d'une tâche d'analyse.
    """
    try:
        job_status = await analysis_service.get_analysis_job_status(job_id)
        if not job_status:
            raise ResourceNotFoundError("Tâche d'analyse", job_id)
        
        return job_status
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut de l'analyse {job_id}: {str(e)}", exc_info=e)
        if isinstance(e, ResourceNotFoundError):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du statut: {str(e)}"
        )


@router.get("/results/{file_id}", response_model=AnomalyResponse)
async def get_analysis_results(
    file_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Récupère les résultats d'analyse pour un fichier spécifique.
    """
    try:
        results = await analysis_service.get_analysis_results(file_id)
        if not results:
            raise ResourceNotFoundError("Résultats d'analyse", file_id)
        
        return results
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des résultats pour le fichier {file_id}: {str(e)}", exc_info=e)
        if isinstance(e, ResourceNotFoundError):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des résultats: {str(e)}"
        )


@router.get("/files", response_model=List[FileUploadResponse])
async def list_files(
    pagination: PaginationParams = Depends(),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Liste les fichiers uploadés avec pagination.
    """
    try:
        files = await analysis_service.list_files(
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        return files
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la liste des fichiers: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de la liste des fichiers: {str(e)}"
        )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Supprime un fichier et toutes ses analyses associées.
    """
    try:
        # Vérification que le fichier existe
        if not await analysis_service.file_exists(file_id):
            raise ResourceNotFoundError("Fichier", file_id)
        
        # Suppression du fichier et des données associées
        await analysis_service.delete_file(file_id)
        
        logger.info(f"Fichier {file_id} supprimé avec succès")
        
        return None
    
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du fichier {file_id}: {str(e)}", exc_info=e)
        if isinstance(e, ResourceNotFoundError):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression du fichier: {str(e)}"
        )