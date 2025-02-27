import asyncio
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.my_fec_generator import MyFECGenerator
from backend.training.train_detector import AnomalyDetectorTrainer
from backend.utils.logging_utils import setup_logging

logger = setup_logging(log_level=logging.INFO)

async def generate_training_data(num_sets: int = 10, entries_per_set: int = 1000):
    """Génère plusieurs jeux de données pour l'entraînement"""
    logger.info(f"Génération de {num_sets} jeux de données d'entraînement")
    
    all_entries = []
    generator = MyFECGenerator()
    
    # Générer plusieurs jeux avec des paramètres différents
    for i in range(num_sets):
        # Varier les paramètres pour chaque jeu
        generator.anomaly_rate = 0.05 + (i * 0.02)  # Augmenter progressivement le taux d'anomalies
        generator.transaction_count = entries_per_set
        
        # Générer les écritures
        entries = generator.generate_entries()
        all_entries.extend(entries)
        
        logger.info(f"Jeu {i+1}/{num_sets} généré avec {len(entries)} écritures")
    
    logger.info(f"Total des écritures générées: {len(all_entries)}")
    return all_entries

async def train_detector(data_dir: str = "data/training", model_dir: str = "data/models"):
    """Entraîne le détecteur d'anomalies"""
    try:
        # Créer les répertoires nécessaires
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(model_dir, exist_ok=True)
        
        # Générer les données d'entraînement
        entries = await generate_training_data(num_sets=10, entries_per_set=1000)
        
        # Créer et entraîner le détecteur
        trainer = AnomalyDetectorTrainer()
        trainer.train(entries)
        
        # Sauvegarder les modèles
        trainer.save_models(model_dir)
        
        logger.info("Entraînement terminé avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'entraînement: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Démarrage de l'entraînement du détecteur d'anomalies")
    
    # Définir les chemins
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data", "training")
    model_dir = os.path.join(base_dir, "data", "models")
    
    # Lancer l'entraînement
    asyncio.run(train_detector(data_dir, model_dir))
