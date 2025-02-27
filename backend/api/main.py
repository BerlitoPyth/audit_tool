"""
Point d'entrée principal de l'API FastAPI.
"""
import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importer après ajustement du PYTHONPATH
from backend.api.api import create_app
from backend.api.endpoints import analysis, reports, generation, models, healthcheck
from backend.core.config import get_settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Créer l'application FastAPI
app = create_app()

# Point de terminaison racine
@app.get("/")
async def root():
    """Point d'entrée racine de l'API"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "env": settings.ENV,
        "docs_url": "/docs",
        "api_base_url": settings.API_V1_STR,
    }

# Enregistrer les routers de healthcheck directement à la racine
app.include_router(
    healthcheck.router,
    prefix="/healthz",
    tags=["Healthcheck"]
)

# Au démarrage de l'application
@app.on_event("startup")
async def startup_event():
    """Exécuté au démarrage de l'application"""
    # Création des répertoires nécessaires
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "models"), exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "generated"), exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "reports"), exist_ok=True)
    os.makedirs(os.path.join(settings.DATA_DIR, "logs"), exist_ok=True)
    
    logger.info(f"Application {settings.APP_NAME} démarrée avec succès en mode {settings.ENV}")

# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )