# Error handling
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception de base pour les erreurs de l'API"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class FileProcessingError(APIError):
    """Exception levée lors du traitement des fichiers"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="FILE_PROCESSING_ERROR",
            details=details
        )


class ModelError(APIError):
    """Exception levée lors de l'utilisation des modèles"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="MODEL_ERROR",
            details=details
        )


class ResourceNotFoundError(APIError):
    """Exception levée lorsqu'une ressource n'est pas trouvée"""
    
    def __init__(self, resource_type: str, resource_id: Union[str, int]):
        super().__init__(
            message=f"{resource_type} avec l'identifiant {resource_id} n'a pas été trouvé",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Gestionnaire pour les APIError"""
    logger.error(f"APIError: {exc.message}", exc_info=exc)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Gestionnaire pour les erreurs de validation"""
    logger.warning(f"Erreur de validation: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Erreur de validation des données",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "errors": exc.errors()
            }
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Gestionnaire pour les exceptions non gérées"""
    logger.error(f"Exception non gérée: {str(exc)}", exc_info=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Erreur interne du serveur",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {"error": str(exc)} if str(exc) else None
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure tous les gestionnaires d'exceptions pour l'application"""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)