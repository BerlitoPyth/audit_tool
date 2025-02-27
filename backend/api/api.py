"""Module principal de l'API"""
from fastapi import APIRouter, FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from typing import Callable

from backend.api.endpoints import analysis, generation, reports, models, healthcheck
from backend.core.config import get_settings
from backend.core.errors import BaseServiceError, FileProcessingError, ResourceNotFoundError

# Configuration du logger
logger = logging.getLogger(__name__)
settings = get_settings()

# Router principal
api_router = APIRouter()

# Enregistrer les différents endpoints
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analyse"])
api_router.include_router(generation.router, prefix="/generation", tags=["Génération"])
api_router.include_router(reports.router, prefix="/reports", tags=["Rapports"])
api_router.include_router(models.router, prefix="/models", tags=["Modèles"])
api_router.include_router(healthcheck.router, prefix="/healthz", tags=["Healthcheck"])

# Middleware de logging des requêtes
async def log_request_middleware(request: Request, call_next):
    """Middleware pour logger les requêtes et leur temps d'exécution"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )
    
    return response

def create_app() -> FastAPI:
    """Crée et configure l'application FastAPI"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="API pour l'outil d'audit financier",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    
    # Configuration CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Ajout du middleware de logging
    app.middleware("http")(log_request_middleware)
    
    # Gestionnaire d'erreurs global
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Gestionnaire d'exceptions global"""
        error_id = f"ERR_{int(time.time())}"
        logger.error(f"Exception non gérée [{error_id}]: {str(exc)}", exc_info=exc)
        
        if isinstance(exc, BaseServiceError):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error_id": error_id,
                    "error": exc.__class__.__name__,
                    "detail": str(exc),
                    "metadata": exc.metadata if hasattr(exc, 'metadata') else None
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_id": error_id,
                "error": "InternalServerError",
                "detail": "Une erreur interne est survenue"
            }
        )
    
    # Monter le router principal
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app