#!/usr/bin/env python
"""Script pour gérer les opérations communes de l'application"""
import os
import sys
import argparse
import logging
import shutil
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings
from backend.training.model_registry import get_model_registry

logger = logging.getLogger(__name__)
settings = get_settings()

def setup_directories():
    """Crée les répertoires nécessaires"""
    dirs = [
        os.path.join(settings.DATA_DIR, "uploads"),
        os.path.join(settings.DATA_DIR, "models"),
        os.path.join(settings.DATA_DIR, "results"),
        os.path.join(settings.DATA_DIR, "logs"),
        os.path.join(settings.DATA_DIR, "stats"),
        os.path.join(settings.DATA_DIR, "generated"),
        os.path.join(settings.DATA_DIR, "temp")
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        logger.info(f"Dossier créé/vérifié : {d}")

def cleanup_temp():
    """Nettoie les fichiers temporaires"""
    temp_dir = os.path.join(settings.DATA_DIR, "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        logger.info("Dossier temporaire nettoyé")

def list_models():
    """Liste les modèles disponibles"""
    registry = get_model_registry()
    models = registry.list_models()
    
    if not models:
        print("Aucun modèle enregistré")
        return
    
    print("\nModèles disponibles:")
    for model in models:
        active = " (ACTIF)" if model.get("is_active") else ""
        print(f"\nVersion: {model['version']}{active}")
        print(f"Créé le: {model.get('created_at', 'N/A')}")
        
        if "metrics" in model:
            print("\nMétriques:")
            for key, value in model["metrics"].items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Gestion de l'application d'audit")
    
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande setup
    setup_parser = subparsers.add_parser("setup", help="Initialise l'environnement")
    
    # Commande cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Nettoie les fichiers temporaires")
    
    # Commande models
    models_parser = subparsers.add_parser("models", help="Gestion des modèles")
    models_parser.add_argument("--list", action="store_true", help="Liste les modèles")
    models_parser.add_argument("--activate", type=str, help="Active un modèle spécifique")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_directories()
        print("Configuration terminée")
        
    elif args.command == "cleanup":
        cleanup_temp()
        print("Nettoyage terminé")
        
    elif args.command == "models":
        if args.list:
            list_models()
        elif args.activate:
            registry = get_model_registry()
            if registry.set_active_model(args.activate):
                print(f"Modèle {args.activate} activé avec succès")
            else:
                print(f"Erreur: Impossible d'activer le modèle {args.activate}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
