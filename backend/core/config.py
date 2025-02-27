"""Configuration de l'application"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import List

class Settings(BaseSettings):
    """Configuration de l'application basée sur les variables d'environnement"""
    
    # Application
    APP_NAME: str = "Audit Tool"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True
    
    # API
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Fichiers
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    class Config:
        """Configuration Pydantic"""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Récupère une instance mise en cache des paramètres"""
    return Settings()