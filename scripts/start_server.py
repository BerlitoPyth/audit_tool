#!/usr/bin/env python
"""
Script de démarrage du serveur web complet (API + interface utilisateur).
Ce script démarre l'API FastAPI et sert les fichiers statiques du frontend.
"""
import os
import sys
import logging
import argparse
import uvicorn
import importlib.util
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from backend.core.config import get_settings
from scripts.manage import setup_directories

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Chemin vers le frontend
settings = get_settings()


def create_app_module():
    """
    Crée un module temporaire contenant l'application complète.
    Cette approche permet d'utiliser le mode rechargement d'uvicorn.
    """
    # Créer le fichier du module app_factory
    app_factory_path = os.path.join(parent_dir, "app_factory.py")
    
    # Contenu du module app_factory
    app_factory_content = """
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.api.api import create_app
from backend.core.config import get_settings

settings = get_settings()
frontend_dir = os.path.join(settings.PROJECT_ROOT, "frontend")

def create_full_app():
    # Créer l'API
    app = create_app()
    
    # Configurer CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Créer les répertoires frontend s'ils n'existent pas
    os.makedirs(frontend_dir, exist_ok=True)
    os.makedirs(os.path.join(frontend_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(frontend_dir, "js"), exist_ok=True)
    
    # Monter les fichiers statiques
    if os.path.exists(os.path.join(frontend_dir, "css")):
        app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
    if os.path.exists(os.path.join(frontend_dir, "js")):
        app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")
    
    # Route pour servir l'interface utilisateur
    @app.get("/", include_in_schema=False)
    async def serve_frontend(request: Request):
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return FileResponse(os.path.join(settings.PROJECT_ROOT, "backend", "templates", "missing_frontend.html"))
    
    return app

app = create_full_app()
"""
    
    # Écrire le fichier
    with open(app_factory_path, "w") as f:
        f.write(app_factory_content)
        
    logger.info(f"Module app_factory créé: {app_factory_path}")
    
    # Créer le répertoire pour les templates par défaut
    templates_dir = os.path.join(parent_dir, "backend", "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    # Créer une page HTML par défaut si le frontend est manquant
    missing_frontend_path = os.path.join(templates_dir, "missing_frontend.html")
    if not os.path.exists(missing_frontend_path):
        missing_frontend_content = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interface non disponible - Audit Tool</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background-color: #f5f5f5;
            text-align: center;
        }
        .container {
            max-width: 800px;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        p {
            font-size: 18px;
            margin-bottom: 15px;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .btn {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Interface utilisateur non disponible</h1>
        <p>Les fichiers de l'interface utilisateur n'ont pas été trouvés.</p>
        <p>Vous pouvez néanmoins accéder à l'API directement:</p>
        <a href="/docs" class="btn">Documentation API</a>
    </div>
</body>
</html>
"""
        with open(missing_frontend_path, "w") as f:
            f.write(missing_frontend_content)
    
    return "app_factory:app"


def main():
    """Fonction principale pour démarrer le serveur"""
    parser = argparse.ArgumentParser(description="Démarrer le serveur d'application complet")
    parser.add_argument("--setup", action="store_true", help="Configurer l'environnement avant le démarrage")
    parser.add_argument("--host", default=settings.HOST, help=f"Adresse d'hôte (défaut: {settings.HOST})")
    parser.add_argument("--port", type=int, default=settings.PORT, help=f"Port d'écoute (défaut: {settings.PORT})")
    parser.add_argument("--no-reload", action="store_true", help="Désactiver le rechargement automatique")
    args = parser.parse_args()
    
    # Configuration de l'environnement si demandé
    if args.setup:
        logger.info("Configuration de l'environnement...")
        setup_directories()
        logger.info("Configuration terminée.")
    
    # Créer le module d'application pour uvicorn
    app_import_string = create_app_module()
    
    # Afficher les informations de démarrage
    print("=== Démarrage de Audit Tool ===")
    print(f"Version: {settings.VERSION}")
    print(f"Environnement: {settings.ENV}")
    print(f"Interface utilisateur: http://{args.host}:{args.port}/")
    print(f"API URL: http://{args.host}:{args.port}/api/v1")
    print(f"Documentation API: http://{args.host}:{args.port}/docs")
    print("==================================================")
    
    # Démarrer le serveur
    use_reload = settings.DEBUG and not args.no_reload
    uvicorn.run(
        app_import_string, 
        host=args.host,
        port=args.port,
        reload=use_reload
    )


if __name__ == "__main__":
    main()
