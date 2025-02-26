# Application configuration
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application avec variables d'environnement"""
    
    # Configuration de base
    APP_NAME: str = "Outil d'Audit Financier"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configuration du serveur
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",      # Frontend React standard
        "http://localhost:8000",      # Backend (pour les tests)
        "http://localhost:*",         # Support pour ports flexibles
    ]
    
    # Configuration de la base de données (si nécessaire)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # Chemins de dossiers importants
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    GENERATED_FEC_DIR: str = os.path.join(DATA_DIR, "generated_fec")
    TRAINED_MODELS_DIR: str = os.path.join(DATA_DIR, "trained_models")
    
    # Configuration des tâches asynchrones
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    
    # Limites de taille de fichiers
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))  # 100 MB par défaut
    
    # Création des dossiers nécessaires au démarrage
    def create_directories(self):
        """Crée les dossiers nécessaires s'ils n'existent pas"""
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.GENERATED_FEC_DIR, exist_ok=True)
        os.makedirs(self.TRAINED_MODELS_DIR, exist_ok=True)
        
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton pour récupérer les paramètres"""
    settings = Settings()
    settings.create_directories()
    return settings