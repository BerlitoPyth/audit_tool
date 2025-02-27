"""Endpoints pour la génération et la gestion des rapports"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Response, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
import logging
import uuid

from backend.models.schemas import ReportRequest, ReportResponse, ReportType, ReportFormat
from backend.core.config import get_settings
from backend.core.errors import ResourceNotFoundError
from backend.services.analysis_service import AnalysisService, get_analysis_service

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Répertoire pour les rapports générés
REPORTS_DIR = os.path.join(settings.DATA_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


async def generate_report_file(
    report_id: str,
    file_id: str,
    report_type: ReportType,
    report_format: ReportFormat,
    options: Dict[str, Any],
    analysis_service: AnalysisService
):
    """
    Génère un fichier de rapport en arrière-plan
    
    Args:
        report_id: Identifiant du rapport
        file_id: Identifiant du fichier analysé
        report_type: Type de rapport
        report_format: Format du rapport
        options: Options spécifiques
        analysis_service: Service d'analyse
    """
    try:
        # Récupérer les résultats d'analyse
        results = await analysis_service.get_analysis_results(file_id)
        if not results:
            logger.error(f"Résultats d'analyse introuvables pour le fichier {file_id}")
            return
        
        # Déterminer le chemin du rapport
        report_file = os.path.join(REPORTS_DIR, f"{report_id}.{report_format.lower()}")
        
        # Créer le contenu du rapport selon le format et le type
        if report_format == ReportFormat.PDF:
            await generate_pdf_report(report_file, results, report_type, options)
        elif report_format == ReportFormat.EXCEL:
            await generate_excel_report(report_file, results, report_type, options)
        elif report_format == ReportFormat.CSV:
            await generate_csv_report(report_file, results, report_type, options)
        elif report_format == ReportFormat.JSON:
            await generate_json_report(report_file, results, report_type, options)
        elif report_format == ReportFormat.HTML:
            await generate_html_report(report_file, results, report_type, options)
        else:
            logger.error(f"Format de rapport non supporté: {report_format}")
            return
            
        logger.info(f"Rapport {report_id} généré avec succès au format {report_format}")
        
        # Mettre à jour les métadonnées du rapport pour indiquer qu'il est prêt
        update_report_metadata(report_id, {
            "status": "completed",
            "file_size": os.path.getsize(report_file),
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport {report_id}: {e}", exc_info=e)
        update_report_metadata(report_id, {
            "status": "failed",
            "error": str(e)
        })


async def generate_pdf_report(file_path: str, results: Any, report_type: ReportType, options: Dict[str, Any]):
    """Génère un rapport au format PDF"""
    # Implémentation factice pour l'instant
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Contenu du rapport PDF pour le type {report_type}\n")
        f.write(f"Anomalies trouvées: {results.anomaly_count}\n")


async def generate_excel_report(file_path: str, results: Any, report_type: ReportType, options: Dict[str, Any]):
    """Génère un rapport au format Excel"""
    # Implémentation factice pour l'instant
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Contenu du rapport Excel pour le type {report_type}\n")
        f.write(f"Anomalies trouvées: {results.anomaly_count}\n")


async def generate_csv_report(file_path: str, results: Any, report_type: ReportType, options: Dict[str, Any]):
    """Génère un rapport au format CSV"""
    # Implémentation factice pour l'instant
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"type,description,confidence,lines\n")
        for anomaly in results.anomalies:
            f.write(f"{anomaly.type},{anomaly.description},{anomaly.confidence_score},{','.join(map(str, anomaly.line_numbers))}\n")


async def generate_json_report(file_path: str, results: Any, report_type: ReportType, options: Dict[str, Any]):
    """Génère un rapport au format JSON"""
    import json
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results.dict(), f, indent=2, default=str)


async def generate_html_report(file_path: str, results: Any, report_type: ReportType, options: Dict[str, Any]):
    """Génère un rapport au format HTML"""
    # Implémentation factice pour l'instant
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Rapport d'analyse</title></head><body>\n")
        f.write(f"<h1>Rapport d'analyse - {report_type}</h1>\n")
        f.write(f"<p>Fichier: {results.filename}</p>\n")
        f.write(f"<p>Total des écritures: {results.total_entries}</p>\n")
        f.write(f"<p>Anomalies détectées: {results.anomaly_count}</p>\n")
        f.write("<h2>Liste des anomalies</h2><ul>\n")
        for anomaly in results.anomalies:
            f.write(f"<li>{anomaly.type}: {anomaly.description} (confiance: {anomaly.confidence_score:.2%})</li>\n")
        f.write("</ul></body></html>\n")


def create_report_metadata(
    report_id: str,
    file_id: str,
    report_type: ReportType,
    report_format: ReportFormat,
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Crée les métadonnées du rapport
    
    Args:
        report_id: Identifiant du rapport
        file_id: Identifiant du fichier analysé
        report_type: Type de rapport
        report_format: Format du rapport
        options: Options spécifiques
    
    Returns:
        Métadonnées du rapport
    """
    now = datetime.now()
    expires_at = now + timedelta(days=30)  # Les rapports expirent après 30 jours
    
    metadata = {
        "report_id": report_id,
        "file_id": file_id,
        "report_type": report_type.value,
        "format": report_format.value,
        "options": options,
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "file_path": os.path.join(REPORTS_DIR, f"{report_id}.{report_format.value.lower()}"),
        "url": f"/api/v1/reports/download/{report_id}"
    }
    
    # Sauvegarder les métadonnées
    metadata_path = os.path.join(REPORTS_DIR, f"{report_id}_meta.json")
    import json
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return metadata


def update_report_metadata(report_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour les métadonnées d'un rapport
    
    Args:
        report_id: Identifiant du rapport
        updates: Mises à jour à appliquer
    
    Returns:
        Métadonnées mises à jour
    """
    metadata_path = os.path.join(REPORTS_DIR, f"{report_id}_meta.json")
    
    # Charger les métadonnées actuelles
    import json
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Appliquer les mises à jour
    metadata.update(updates)
    
    # Sauvegarder les métadonnées mises à jour
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return metadata


def get_report_metadata(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les métadonnées d'un rapport
    
    Args:
        report_id: Identifiant du rapport
    
    Returns:
        Métadonnées du rapport ou None si introuvable
    """
    metadata_path = os.path.join(REPORTS_DIR, f"{report_id}_meta.json")
    
    if not os.path.exists(metadata_path):
        return None
    
    import json
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Génère un rapport à partir des résultats d'analyse
    """
    try:
        # Vérifier si le fichier a été analysé
        if not await analysis_service.get_analysis_results(request.file_id):
            raise ResourceNotFoundError("Résultats d'analyse", request.file_id)
        
        # Créer un ID pour le rapport
        report_id = str(uuid.uuid4())
        
        # Créer les métadonnées du rapport
        metadata = create_report_metadata(
            report_id=report_id,
            file_id=request.file_id,
            report_type=request.report_type,
            report_format=request.format,
            options=request.options
        )
        
        # Générer le rapport en arrière-plan
        background_tasks.add_task(
            generate_report_file,
            report_id=report_id,
            file_id=request.file_id,
            report_type=request.report_type,
            report_format=request.format,
            options=request.options,
            analysis_service=analysis_service
        )
        
        # Renvoyer une réponse immédiate
        return ReportResponse(
            report_id=report_id,
            file_id=request.file_id,
            report_type=request.report_type,
            format=request.format,
            url=metadata["url"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            expires_at=datetime.fromisoformat(metadata["expires_at"]),
            size_bytes=None  # Pas encore disponible
        )
        
    except Exception as e:
        if isinstance(e, ResourceNotFoundError):
            raise
        logger.error(f"Erreur lors de la génération du rapport: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport: {str(e)}")


@router.get("/status/{report_id}")
async def get_report_status(report_id: str):
    """
    Récupère le statut d'un rapport
    """
    try:
        metadata = get_report_metadata(report_id)
        if not metadata:
            raise ResourceNotFoundError("Rapport", report_id)
        
        return {
            "report_id": metadata["report_id"],
            "status": metadata["status"],
            "created_at": metadata["created_at"],
            "completed_at": metadata.get("completed_at"),
            "file_size": metadata.get("file_size"),
            "error": metadata.get("error")
        }
        
    except Exception as e:
        if isinstance(e, ResourceNotFoundError):
            raise
        logger.error(f"Erreur lors de la récupération du statut du rapport: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {str(e)}")


@router.get("/download/{report_id}")
async def download_report(report_id: str):
    """
    Télécharge un rapport
    """
    try:
        # Vérifier si le rapport existe
        metadata = get_report_metadata(report_id)
        if not metadata:
            raise ResourceNotFoundError("Rapport", report_id)
        
        # Vérifier si le rapport est prêt
        if metadata["status"] != "completed":
            raise HTTPException(status_code=404, detail=f"Le rapport {report_id} n'est pas encore prêt")
        
        # Déterminer le chemin du fichier
        file_path = metadata["file_path"]
        if not os.path.exists(file_path):
            raise ResourceNotFoundError("Fichier de rapport", report_id)
        
        # Déterminer le type de contenu
        content_type_map = {
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
            "html": "text/html"
        }
        content_type = content_type_map.get(metadata["format"].lower(), "application/octet-stream")
        
        # Lire le fichier et le renvoyer
        with open(file_path, "rb") as f:
            content = f.read()
            
        # Construire le nom de fichier de téléchargement
        filename = f"report_{report_id}_{metadata['report_type']}.{metadata['format'].lower()}"
        
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        if isinstance(e, ResourceNotFoundError) or isinstance(e, HTTPException):
            raise
        logger.error(f"Erreur lors du téléchargement du rapport: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement: {str(e)}")


@router.get("/list", response_model=List[ReportResponse])
async def list_reports(
    file_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Liste les rapports disponibles avec pagination
    """
    try:
        reports = []
        
        # Charger tous les fichiers de métadonnées
        for filename in os.listdir(REPORTS_DIR):
            if not filename.endswith("_meta.json"):
                continue
            
            # Charger les métadonnées
            with open(os.path.join(REPORTS_DIR, filename), "r", encoding="utf-8") as f:
                import json
                metadata = json.load(f)
            
            # Filtrer par file_id si spécifié
            if file_id and metadata["file_id"] != file_id:
                continue
            
            # Convertir les chaînes ISO en objets datetime
            created_at = datetime.fromisoformat(metadata["created_at"])
            expires_at = datetime.fromisoformat(metadata["expires_at"]) if "expires_at" in metadata else None
            
            reports.append(ReportResponse(
                report_id=metadata["report_id"],
                file_id=metadata["file_id"],
                report_type=ReportType(metadata["report_type"]),
                format=ReportFormat(metadata["format"]),
                url=metadata["url"],
                created_at=created_at,
                expires_at=expires_at,
                size_bytes=metadata.get("file_size")
            ))
        
        # Trier par date de création (plus récent en premier)
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return reports[start_idx:end_idx]
        
    except Exception as e:
        logger.error(f"Erreur lors de la liste des rapports: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des rapports: {str(e)}")
