# FastAPI entry point
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from backend.core.config import get_settings
from backend.core.errors import setup_exception_handlers
from backend.api.endpoints import analysis, reports

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Actions à l'initialisation (chargement des modèles, etc.)
    logger.info("Démarrage de l'application d'audit financier")
    logger.info(f"Mode DEBUG: {settings.DEBUG}")
    
    try:
        # Préchargement des modèles et autres ressources ici
        logger.info("Initialisation des ressources...")
        # Placeholder pour le chargement des modèles
        # models.load_models()
        yield
    finally:
        # Nettoyage des ressources à la fermeture
        logger.info("Fermeture de l'application, nettoyage des ressources...")


# Création de l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API pour l'outil d'audit financier avec détection d'anomalies",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de la gestion des erreurs
setup_exception_handlers(app)

# Inclusion des routers
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analysis", tags=["analysis"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])


@app.get("/")
async def root():
    """Endpoint racine pour vérifier que l'API fonctionne"""
    return {"message": "Outil d'audit financier API", "status": "running"}


@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )