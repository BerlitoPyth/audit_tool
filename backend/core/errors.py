"""Définition des exceptions personnalisées pour l'application"""
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class BaseServiceError(Exception):
    """Classe de base pour les erreurs de service"""
    
    def __init__(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        self.message = message
        self.metadata = metadata or {}
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return self.message


class FileProcessingError(BaseServiceError):
    """Erreur lors du traitement d'un fichier"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = status.HTTP_400_BAD_REQUEST


class ResourceNotFoundError(BaseServiceError):
    """Erreur lorsqu'une ressource n'est pas trouvée"""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} avec l'identifiant '{resource_id}' introuvable"
        metadata = {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        super().__init__(message, metadata)
        self.status_code = status.HTTP_404_NOT_FOUND


class ValidationError(BaseServiceError):
    """Erreur de validation des données"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class AuthenticationError(BaseServiceError):
    """Erreur d'authentification"""
    
    def __init__(self, message: str = "Authentification échouée"):
        super().__init__(message)
        self.status_code = status.HTTP_401_UNAUTHORIZED


class AuthorizationError(BaseServiceError):
    """Erreur d'autorisation"""
    
    def __init__(self, message: str = "Action non autorisée"):
        super().__init__(message)
        self.status_code = status.HTTP_403_FORBIDDEN


class ConfigurationError(BaseServiceError):
    """Erreur de configuration"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ExternalServiceError(BaseServiceError):
    """Erreur d'un service externe"""
    
    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        metadata = details or {}
        metadata["service_name"] = service_name
        super().__init__(f"Erreur du service {service_name}: {message}", metadata)
        self.status_code = status.HTTP_502_BAD_GATEWAY


class ModelError(BaseServiceError):
    """Erreur liée aux modèles ML"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure les gestionnaires d'exceptions pour l'application"""
    
    @app.exception_handler(FileProcessingError)
    async def file_processing_error_handler(request: Request, exc: FileProcessingError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "detail": str(exc),
                "metadata": exc.metadata
            }
        )
    
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_error_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "detail": str(exc),
                "metadata": exc.metadata
            }
        )
    
    @app.exception_handler(ModelError)
    async def model_error_handler(request: Request, exc: ModelError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "detail": str(exc),
                "metadata": exc.metadata
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Gestionnaire pour les exceptions non gérées"""
        logger.error(f"Exception non gérée: {str(exc)}", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "Une erreur interne est survenue"
            }
        )