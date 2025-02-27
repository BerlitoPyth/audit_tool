import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.models.schemas import ReportResponse
from backend.core.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


class ReportService:
    """Service de génération et gestion des rapports"""
    
    def __init__(self):
        """Initialisation du service"""
        self._reports = {}  # Stockage en mémoire des rapports (à remplacer par une BDD)
    
    async def generate_report(
        self, file_id: str, report_type: str, options: Dict[str, Any] = None
    ) -> ReportResponse:
        """
        Génère un nouveau rapport
        
        Args:
            file_id: ID du fichier analysé
            report_type: Type de rapport (pdf, excel, etc.)
            options: Options de génération supplémentaires
            
        Returns:
            Les détails du rapport généré
        """
        report_id = str(uuid.uuid4())
        now = datetime.now()
        download_url = f"/api/v1/reports/{report_id}/download"
        
        # Simulation de génération de rapport
        report = ReportResponse(
            report_id=report_id,
            file_id=file_id,
            report_type=report_type,
            creation_timestamp=now,
            download_url=download_url,
            status="completed",
            message="Rapport généré avec succès"
        )
        
        # Stocker le rapport
        self._reports[report_id] = report.dict()
        
        logger.info(f"Rapport {report_id} généré pour le fichier {file_id}, type: {report_type}")
        
        return report
    
    async def get_report(self, report_id: str) -> Optional[ReportResponse]:
        """
        Récupère un rapport par son ID
        
        Args:
            report_id: ID du rapport
            
        Returns:
            Le rapport ou None s'il n'existe pas
        """
        if report_id not in self._reports:
            return None
        
        return ReportResponse(**self._reports[report_id])
    
    async def list_reports(self, file_id: Optional[str] = None) -> List[ReportResponse]:
        """
        Liste les rapports disponibles
        
        Args:
            file_id: Optionnel, filtre par ID de fichier
            
        Returns:
            Liste des rapports
        """
        result = []
        
        for report_data in self._reports.values():
            # Filtrer par file_id si spécifié
            if file_id and report_data["file_id"] != file_id:
                continue
            
            result.append(ReportResponse(**report_data))
        
        return result
    
    async def delete_report(self, report_id: str) -> bool:
        """
        Supprime un rapport
        
        Args:
            report_id: ID du rapport à supprimer
            
        Returns:
            True si supprimé, False sinon
            
        Raises:
            ResourceNotFoundError: Si le rapport n'existe pas
        """
        if report_id not in self._reports:
            raise ResourceNotFoundError("Rapport", report_id)
        
        del self._reports[report_id]
        logger.info(f"Rapport {report_id} supprimé")
        
        return True


# Instance globale singleton du service
_report_service = None

def get_report_service() -> ReportService:
    """Récupère l'instance singleton du service de rapports"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
