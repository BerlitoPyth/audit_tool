#!/usr/bin/env python
"""Script pour démarrer l'API"""
import os
import sys
import uvicorn
import logging

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings

def main():
    """Démarre le serveur API"""
    settings = get_settings()
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"\n=== Démarrage de {settings.APP_NAME} ===")
    print(f"Version: {settings.VERSION}")
    print(f"Environnement: {settings.ENV}")
    print(f"API URL: http://{settings.HOST}:{settings.PORT}{settings.API_V1_STR}")
    print(f"Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 50 + "\n")
    
    # Démarrer le serveur
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

if __name__ == "__main__":
    main()
