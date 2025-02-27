"""Point d'entrée principal de l'application FastAPI"""
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from backend.api.api import create_app
from backend.core.config import get_settings

settings = get_settings()

# Créer l'application FastAPI
app = create_app()

# Ajouter une redirection de la racine vers la documentation
@app.get("/")
async def root():
    """Redirige vers la documentation Swagger"""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
