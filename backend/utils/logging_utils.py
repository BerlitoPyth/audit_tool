"""Utilitaires de journalisation pour l'application"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from backend.core.config import get_settings

def setup_logging(log_level=logging.INFO, log_to_file=False):
    """
    Configure le système de journalisation
    
    Args:
        log_level: Niveau de journalisation (logging.INFO, logging.DEBUG, etc.)
        log_to_file: Si True, journalise également dans un fichier
        
    Returns:
        Logger configuré
    """
    settings = get_settings()
    
    # Formatter avec couleurs pour la console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Formatter pour les fichiers
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levellevel)s - %(pathname)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Logger racine
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Supprimer les handlers existants
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # Handler fichier si demandé
    if log_to_file:
        # Créer le répertoire des logs s'il n'existe pas
        log_dir = os.path.join(settings.PROJECT_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Nom du fichier de log avec date
        log_file = os.path.join(
            log_dir,
            f"app_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # Ajouter le handler fichier
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    
    # Loggers pour les bibliothèques tierces
    for logger_name in ['uvicorn', 'fastapi', 'sqlalchemy']:
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers = []
        lib_logger.propagate = True
    
    return logger

def log_exception(logger, e, message="Une exception s'est produite"):
    """Log les détails complets d'une exception"""
    logger.error(f"{message}: {str(e)}")
    logger.error(traceback.format_exc())

def log_request(logger, request):
    """Log les détails d'une requête HTTP"""
    logger.debug(f"URL: {request.url}")
    logger.debug(f"Method: {request.method}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Query params: {dict(request.query_params)}")
    logger.debug(f"Path params: {dict(request.path_params)}")
