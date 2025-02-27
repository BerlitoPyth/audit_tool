"""Utilitaires pour l'entraînement des modèles"""
import os
import sys
import json
import logging
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def run_training_job(
    job_id: str,
    num_sets: int = 10,
    entries_per_set: int = 1000,
    description: Optional[str] = None,
    activate: bool = False
) -> None:
    """
    Exécute un job d'entraînement de modèle
    
    Args:
        job_id: Identifiant unique du job
        num_sets: Nombre de jeux de données à générer
        entries_per_set: Nombre d'écritures par jeu de données
        description: Description du modèle
        activate: Si True, active le modèle après l'entraînement
    """
    try:
        # Création des fichiers de log et de statut
        logs_dir = os.path.join(settings.DATA_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"train_{job_id}.log")
        status_file = os.path.join(logs_dir, f"train_{job_id}_status.json")
        
        # Initialisation du statut
        status = {
            "job_id": job_id,
            "status": "initializing",
            "progress": 0,
            "message": "Initialisation de l'entraînement",
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        _save_status(status_file, status)
        
        # Construction de la ligne de commande
        train_script = os.path.join(settings.PROJECT_ROOT, "scripts", "train_detector.py")
        cmd = [
            sys.executable,
            train_script,
            "--num-sets", str(num_sets),
            "--entries-per-set", str(entries_per_set),
            "--evaluate"
        ]
        
        if description:
            cmd.extend(["--description", description])
            
        if activate:
            cmd.append("--activate")
        
        # Redirection des sorties vers le fichier de log
        with open(log_file, "w", encoding="utf-8") as log:
            # Mettre à jour le statut
            status["status"] = "running"
            status["message"] = "Entraînement en cours..."
            status["progress"] = 10
            _save_status(status_file, status)
            
            # Lancer le processus d'entraînement
            logger.info(f"Démarrage de l'entraînement pour le job {job_id}")
            logger.info(f"Commande: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Mettre à jour le statut pendant l'exécution
            progress_values = [20, 30, 40, 50, 60, 70, 80, 90]
            for progress in progress_values:
                # Attendre un peu
                await asyncio.sleep(2)
                
                # Vérifier si le processus est toujours en cours
                if process.poll() is not None:
                    break
                
                # Mettre à jour le statut
                status["progress"] = progress
                _save_status(status_file, status)
            
            # Attendre la fin du processus
            returncode = process.wait()
            
            # Mettre à jour le statut final
            status["end_time"] = datetime.now().isoformat()
            
            if returncode == 0:
                status["status"] = "completed"
                status["message"] = "Entraînement terminé avec succès"
                status["progress"] = 100
            else:
                status["status"] = "failed"
                status["message"] = f"Échec de l'entraînement (code {returncode})"
                status["progress"] = 100
                
            _save_status(status_file, status)
            
            logger.info(f"Entraînement terminé pour le job {job_id} avec le code {returncode}")
            
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du job d'entraînement {job_id}: {str(e)}", exc_info=True)
        
        # Mettre à jour le statut en cas d'erreur
        try:
            status = {
                "job_id": job_id,
                "status": "failed",
                "progress": 100,
                "message": f"Erreur: {str(e)}",
                "start_time": status.get("start_time", datetime.now().isoformat()),
                "end_time": datetime.now().isoformat()
            }
            _save_status(status_file, status)
        except Exception:
            pass

def _save_status(status_file: str, status: Dict[str, Any]) -> None:
    """
    Sauvegarde le statut dans un fichier JSON
    
    Args:
        status_file: Chemin du fichier de statut
        status: Dictionnaire de statut
    """
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
