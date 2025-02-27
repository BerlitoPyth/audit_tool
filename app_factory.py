
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
