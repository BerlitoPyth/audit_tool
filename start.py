#!/usr/bin/env python
"""
Script de démarrage combiné pour l'application d'audit.
Effectue la configuration initiale puis lance l'API.
"""
import os
import sys
import argparse
import logging
import subprocess

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Configure l'environnement (crée les dossiers nécessaires)"""
    try:
        from scripts.manage import setup_directories
        logger.info("Configuration de l'environnement...")
        setup_directories()
        logger.info("Configuration terminée")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la configuration: {str(e)}")
        return False

def start_api():
    """Démarre le serveur API"""
    try:
        # Utilisation de subprocess pour démarrer un nouveau processus
        api_script = os.path.join("scripts", "start_api.py")
        
        # Déterminer le chemin vers Python
        python_path = sys.executable
        
        logger.info("Démarrage du serveur API...")
        process = subprocess.Popen(
            [python_path, api_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Ligne par ligne
        )
        
        # Afficher la sortie en temps réel
        for line in process.stdout:
            print(line, end='')
            
        # Attendre la fin du processus
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"Le serveur API s'est arrêté avec le code d'erreur {process.returncode}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de l'API: {str(e)}")
        return False

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Démarrage de l'application d'audit")
    
    parser.add_argument("--skip-setup", action="store_true", help="Ignorer la configuration initiale")
    
    args = parser.parse_args()
    
    # Étape 1: Configuration (sauf si --skip-setup est spécifié)
    if not args.skip_setup:
        if not setup_environment():
            sys.exit(1)
    
    # Étape 2: Démarrage de l'API
    if not start_api():
        sys.exit(1)

if __name__ == "__main__":
    main()
