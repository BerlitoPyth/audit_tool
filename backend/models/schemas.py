from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class AnomalyType(str, Enum):
    """Types d'anomalies possibles dans les fichiers FEC"""
    MISSING_DATA = "missing_data"
    INCORRECT_FORMAT = "incorrect_format"
    DUPLICATE_ENTRY = "duplicate_entry"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    BALANCE_MISMATCH = "balance_mismatch"
    DATE_INCONSISTENCY = "date_inconsistency"
    CALCULATION_ERROR = "calculation_error"
    CUSTOM = "custom"


class AnomalyBase(BaseModel):
    """Modèle de base pour une anomalie"""
    type: AnomalyType
    description: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    line_numbers: Optional[List[int]] = None
    related_data: Optional[Dict[str, Any]] = None


class Anomaly(AnomalyBase):
    """Modèle complet d'anomalie avec ID"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detected_at: datetime = Field(default_factory=datetime.now)


class AnomalyResponse(BaseModel):
    """Réponse contenant une liste d'anomalies"""
    anomalies: List[Anomaly]
    total_count: int
    file_id: str
    analysis_duration_ms: float


class AnalysisRequest(BaseModel):
    """Requête pour lancer une analyse"""
    file_id: str
    analysis_type: str = "standard"
    options: Optional[Dict[str, Any]] = None


class AnalysisStatus(str, Enum):
    """Statut possible d'une analyse"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJobStatus(BaseModel):
    """Statut d'une tâche d'analyse"""
    job_id: str
    file_id: str
    status: AnalysisStatus
    progress: float = 0.0
    message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None


class FECEntryBase(BaseModel):
    """Structure de base d'une entrée FEC (Format d'Échange Comptable)"""
    journal_code: str
    journal_lib: str
    ecr_num: str
    ecr_date: datetime
    compte_num: str
    compte_lib: str
    comp_aux_num: Optional[str] = None
    comp_aux_lib: Optional[str] = None
    piece_ref: str
    piece_date: datetime
    ecriture_lib: str
    debit_montant: float = 0.0
    credit_montant: float = 0.0
    ecriture_date: datetime
    validation_date: Optional[datetime] = None


class FECEntry(FECEntryBase):
    """Entrée FEC complète avec ID"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ReportType(str, Enum):
    """Types de rapports disponibles"""
    ANOMALY_SUMMARY = "anomaly_summary"
    DETAILED_AUDIT = "detailed_audit"
    EXECUTIVE_SUMMARY = "executive_summary"
    CUSTOM = "custom"


class ReportRequest(BaseModel):
    """Requête pour générer un rapport"""
    file_id: str
    report_type: ReportType
    options: Optional[Dict[str, Any]] = None
    
    @validator('options')
    def validate_options_for_custom(cls, v, values):
        """Valide que les options sont présentes pour un rapport personnalisé"""
        if values.get('report_type') == ReportType.CUSTOM and not v:
            raise ValueError("Les options sont requises pour un rapport personnalisé")
        return v


class ReportStatus(str, Enum):
    """Statut possible d'un rapport"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportJobStatus(BaseModel):
    """Statut d'une tâche de génération de rapport"""
    job_id: str
    file_id: str
    report_type: ReportType
    status: ReportStatus
    progress: float = 0.0
    message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    report_url: Optional[str] = None


class FileUploadResponse(BaseModel):
    """Réponse après l'upload d'un fichier"""
    file_id: str
    filename: str
    size_bytes: int
    upload_timestamp: datetime
    content_type: str
    status: str = "uploaded"
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """Paramètres de pagination"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)