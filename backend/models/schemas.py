"""
Schémas de données pour l'application d'audit.
Ce module définit les structures de données utilisées dans l'application.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import uuid


class AnomalyType(str, Enum):
    """Types d'anomalies que le système peut détecter"""
    DUPLICATE_ENTRY = "duplicate_entry"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    MISSING_DATA = "missing_data"
    DATE_INCONSISTENCY = "date_inconsistency"
    BALANCE_MISMATCH = "balance_mismatch"
    UNUSUAL_ACCOUNT_ACTIVITY = "unusual_account_activity"
    OTHER = "other"


class AnalysisType(str, Enum):
    """Types d'analyses disponibles"""
    STANDARD = "standard"
    ADVANCED = "advanced"
    DUPLICATE_CHECK = "duplicate_check"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class AnalysisStatus(str, Enum):
    """Statuts possibles pour une tâche d'analyse"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportType(str, Enum):
    """Types de rapports disponibles"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"
    EXPORT = "export"


class ReportFormat(str, Enum):
    """Formats de rapports disponibles"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class Anomaly(BaseModel):
    """Représente une anomalie détectée dans les données"""
    id: str = Field(..., description="Identifiant unique de l'anomalie")
    type: AnomalyType = Field(..., description="Type d'anomalie")
    description: str = Field(..., description="Description de l'anomalie")
    confidence_score: float = Field(..., ge=0, le=1, description="Score de confiance (0-1)")
    line_numbers: List[int] = Field(..., description="Numéros des lignes concernées")
    related_data: Dict[str, Any] = Field(default_factory=dict, description="Données associées à l'anomalie")
    detected_at: datetime = Field(..., description="Horodatage de la détection")

    class Config:
        """Configuration du modèle"""
        json_schema_extra = {
            "example": {
                "id": "anom-123",
                "type": "suspicious_pattern",
                "description": "Montant suspicieusement rond",
                "confidence_score": 0.85,
                "line_numbers": [42, 43],
                "related_data": {
                    "amount": 10000.00,
                    "account": "512000"
                },
                "detected_at": "2023-01-15T14:30:00"
            }
        }


class AnomalyResponse(BaseModel):
    """Réponse contenant les anomalies détectées"""
    file_id: str = Field(..., description="Identifiant du fichier analysé")
    filename: Optional[str] = Field(None, description="Nom du fichier analysé")
    total_entries: int = Field(..., description="Nombre total d'entrées analysées")
    anomaly_count: int = Field(..., description="Nombre d'anomalies détectées")
    anomalies: List[Anomaly] = Field(..., description="Liste des anomalies détectées")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage de l'analyse")
    processing_time_ms: Optional[int] = Field(None, description="Temps de traitement en millisecondes")


class AnalysisJobStatus(BaseModel):
    """Statut d'une tâche d'analyse"""
    job_id: str = Field(..., description="Identifiant unique de la tâche")
    file_id: str = Field(..., description="Identifiant du fichier analysé")
    status: AnalysisStatus = Field(..., description="Statut de l'analyse")
    progress: float = Field(..., ge=0, le=100, description="Progression (0-100%)")
    created_at: datetime = Field(..., description="Date de création")
    started_at: Optional[datetime] = Field(None, description="Date de début")
    completed_at: Optional[datetime] = Field(None, description="Date de fin")
    error: Optional[str] = Field(None, description="Message d'erreur (si échec)")
    result_path: Optional[str] = Field(None, description="Chemin vers les résultats")


class AnalysisRequest(BaseModel):
    """Requête pour lancer une analyse"""
    file_id: str = Field(..., description="Identifiant du fichier à analyser")
    analysis_type: AnalysisType = Field(default=AnalysisType.STANDARD, description="Type d'analyse")
    options: Dict[str, Any] = Field(default_factory=dict, description="Options d'analyse")


class FileUploadResponse(BaseModel):
    """Réponse après upload d'un fichier"""
    file_id: str = Field(..., description="Identifiant unique du fichier")
    filename: str = Field(..., description="Nom du fichier")
    size_bytes: int = Field(..., description="Taille du fichier en octets")
    upload_timestamp: datetime = Field(..., description="Date et heure de l'upload")
    content_type: str = Field(..., description="Type MIME du fichier")
    status: str = Field(..., description="Statut de l'upload")
    message: Optional[str] = Field(None, description="Message supplémentaire")


class PaginationParams(BaseModel):
    """Paramètres de pagination"""
    page: int = Field(1, ge=1, description="Numéro de page (commence à 1)")
    page_size: int = Field(20, ge=1, le=100, description="Nombre d'éléments par page")


class ReportRequest(BaseModel):
    """Requête pour la génération d'un rapport"""
    file_id: str = Field(..., description="Identifiant du fichier à analyser")
    report_type: ReportType = Field(default=ReportType.SUMMARY, description="Type de rapport")
    format: ReportFormat = Field(default=ReportFormat.PDF, description="Format du rapport")
    include_visualizations: bool = Field(default=True, description="Inclure des visualisations")
    options: Dict[str, Any] = Field(default_factory=dict, description="Options spécifiques au rapport")

    class Config:
        """Configuration du modèle"""
        json_schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "report_type": "detailed",
                "format": "pdf",
                "include_visualizations": True,
                "options": {
                    "include_raw_data": False,
                    "sort_by": "confidence_score"
                }
            }
        }


class ReportResponse(BaseModel):
    """Réponse à une requête de génération de rapport"""
    report_id: str = Field(..., description="Identifiant unique du rapport")
    file_id: str = Field(..., description="Identifiant du fichier analysé")
    report_type: ReportType = Field(..., description="Type de rapport")
    format: ReportFormat = Field(..., description="Format du rapport")
    url: str = Field(..., description="URL pour télécharger le rapport")
    created_at: datetime = Field(..., description="Date de création")
    expires_at: Optional[datetime] = Field(None, description="Date d'expiration")
    size_bytes: Optional[int] = Field(None, description="Taille du rapport en octets")