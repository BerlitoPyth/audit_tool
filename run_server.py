import os
import sys
import uvicorn
import logging
from pathlib import Path

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.utils.logging_utils import setup_logging
from backend.core.config import get_settings

def main():
    # Configuration du logging
    setup_logging(log_level=logging.INFO, log_to_file=True)
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    
    # Assurez-vous que les répertoires nécessaires existent
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.RESULTS_DIR, exist_ok=True)
    os.makedirs(settings.JOBS_DIR, exist_ok=True)
    
    logger.info(f"Démarrage du serveur {settings.APP_NAME} sur {settings.HOST}:{settings.PORT}")
    logger.info(f"Répertoires de données: {settings.DATA_DIR}")
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()
