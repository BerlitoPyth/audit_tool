#!/usr/bin/env python
"""
Script pour entraîner le détecteur d'anomalies sur des données générées.
Ce script permet de créer des modèles ML qui seront utilisés par le détecteur.
"""
import asyncio
import sys
import os
import logging
import argparse
from datetime import datetime
import time
import uuid
import numpy as np
import joblib  # Import ajouté pour résoudre l'erreur

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.my_fec_generator import MyFECGenerator
from backend.training.train_detector import AnomalyDetectorTrainer
from backend.models.schemas import Anomaly, AnomalyType
from backend.core.config import get_settings
from backend.training.model_registry import get_model_registry

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

async def generate_training_data(num_sets=10, entries_per_set=1000, anomaly_rates=None):
    """
    Génère plusieurs jeux de données pour l'entraînement
    
    Args:
        num_sets: Nombre de jeux de données à générer
        entries_per_set: Nombre d'écritures par jeu de données
        anomaly_rates: Liste des taux d'anomalies à utiliser
        
    Returns:
        Liste des écritures générées
    """
    if anomaly_rates is None:
        # Taux d'anomalies croissants
        anomaly_rates = [0.05 + (i * 0.02) for i in range(num_sets)]
    
    logger.info(f"Génération de {num_sets} jeux de données d'entraînement")
    all_entries = []
    
    # Pour chaque jeu de données
    for i, rate in enumerate(anomaly_rates[:num_sets]):
        # Créer un générateur avec le taux d'anomalies spécifié
        generator = MyFECGenerator(
            company_name=f"TRAINING_SET_{i+1}",
            start_date="2023-01-01",
            end_date="2023-12-31",
            transaction_count=entries_per_set,
            anomaly_rate=rate
        )
        
        # Générer les écritures
        entries = generator.generate_entries()
        all_entries.extend(entries)
        
        logger.info(f"Jeu {i+1}/{num_sets} généré avec {len(entries)} écritures (taux d'anomalies: {rate:.2f})")
    
    logger.info(f"Total des entrées générées: {len(all_entries)}")
    return all_entries

async def evaluate_model(trainer, test_entries):
    """
    Évalue les performances du modèle sur un jeu de test
    
    Args:
        trainer: Trainer avec modèles entraînés
        test_entries: Jeu de données de test
        
    Returns:
        Dictionnaire des métriques
    """
    logger.info(f"Évaluation des performances sur {len(test_entries)} entrées de test")
    metrics = {}
    
    # Extraction des caractéristiques
    features = trainer._extract_features(test_entries)
    
    # Évaluer chaque modèle
    for name, model in trainer.models.items():
        try:
            X = trainer.scalers[name].transform(features[name])
            predictions = model.predict(X)
            anomaly_count = sum(1 for p in predictions if p == -1)
            scores = model.score_samples(X)
            
            # Calcul des métriques
            metrics[f"{name}_anomaly_rate"] = anomaly_count / len(test_entries)
            metrics[f"{name}_score_mean"] = float(np.mean(scores))
            metrics[f"{name}_score_std"] = float(np.std(scores))
            
            logger.info(f"Modèle {name}: {anomaly_count} anomalies détectées sur {len(test_entries)} entrées")
            logger.info(f"Score moyen: {metrics[f'{name}_score_mean']:.4f}, Écart-type: {metrics[f'{name}_score_std']:.4f}")
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation du modèle {name}: {str(e)}")
    
    return metrics

async def train_and_save_models(options):
    """
    Entraîne les modèles et les sauvegarde
    
    Args:
        options: Options pour l'entraînement
    """
    try:
        start_time = time.time()
        
        # Créer les répertoires
        model_dir = os.path.join(settings.DATA_DIR, "models")
        os.makedirs(model_dir, exist_ok=True)
        
        # Générer les données d'entraînement
        logger.info("Génération des données d'entraînement...")
        entries = await generate_training_data(
            num_sets=options.num_sets,
            entries_per_set=options.entries_per_set
        )
        
        # Créer et entraîner le détecteur
        logger.info(f"Entraînement du détecteur sur {len(entries)} écritures...")
        trainer = AnomalyDetectorTrainer()
        trainer.train(entries)
        
        # Générer une version pour ce modèle
        version = options.version or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Créer les chemins de fichiers pour ce modèle
        model_files = {}
        
        # Sauvegarder les modèles avec la version
        for name in trainer.models.keys():
            model_path = os.path.join(model_dir, f"{name}_model_{version}.joblib")
            scaler_path = os.path.join(model_dir, f"{name}_scaler_{version}.joblib")
            
            joblib.dump(trainer.models[name], model_path)
            joblib.dump(trainer.scalers[name], scaler_path)
            
            model_files[f"{name}_model"] = model_path
            model_files[f"{name}_scaler"] = scaler_path
        
        # Calculer le temps d'entraînement
        training_time = time.time() - start_time
        
        # Évaluer les performances si demandé
        metrics = {
            "training_time": training_time,
            "training_samples": len(entries),
            "training_date": datetime.now().isoformat()
        }
        
        if options.evaluate:
            # Générer un jeu de test
            test_generator = MyFECGenerator(
                company_name="TEST_SET",
                anomaly_rate=0.1  # 10% d'anomalies dans le jeu de test
            )
            test_entries = test_generator.generate_entries(count=options.test_size or 500)
            
            # Évaluer le modèle
            test_metrics = await evaluate_model(trainer, test_entries)
            metrics.update(test_metrics)
        
        # Enregistrer le modèle dans le registre
        registry = get_model_registry()
        registry.register_model(
            version=version,
            model_files=model_files,
            metrics=metrics,
            metadata={
                "description": options.description or "Modèle de détection d'anomalies",
                "anomaly_rates": [0.05 + (i * 0.02) for i in range(options.num_sets)],
                "command_line": " ".join(sys.argv),
            }
        )
        
        # Définir comme modèle actif si demandé ou s'il n'y a pas de modèle actif
        current_active = registry.get_active_model_info()
        if options.activate or not current_active:
            registry.set_active_model(version)
            logger.info(f"Modèle version {version} défini comme actif")
        
        logger.info(f"Modèle entraîné et sauvegardé avec succès, version: {version}")
        
        # Afficher un récapitulatif
        logger.info("Récapitulatif de l'entraînement:")
        logger.info(f"- Version: {version}")
        logger.info(f"- Échantillons d'entraînement: {len(entries)}")
        logger.info(f"- Temps d'entraînement: {training_time:.2f} secondes")
        if options.evaluate:
            for key, value in test_metrics.items():
                logger.info(f"- {key}: {value:.4f}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'entraînement: {str(e)}", exc_info=True)
        sys.exit(1)

def parse_args():
    """Analyse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Entraîne le détecteur d'anomalies")
    
    parser.add_argument("--num-sets", type=int, default=10,
                       help="Nombre de jeux de données à générer")
    
    parser.add_argument("--entries-per-set", type=int, default=500,
                       help="Nombre d'écritures par jeu de données")
    
    parser.add_argument("--evaluate", action="store_true",
                       help="Évaluer les performances après l'entraînement")
    
    parser.add_argument("--test-size", type=int, default=500,
                       help="Nombre d'écritures pour le jeu de test")
    
    parser.add_argument("--version", type=str, default=None,
                       help="Version du modèle à enregistrer (défaut: date/heure)")
    
    parser.add_argument("--description", type=str, default=None,
                       help="Description du modèle")
    
    parser.add_argument("--activate", action="store_true",
                       help="Activer ce modèle après l'entraînement")
    
    return parser.parse_args()

if __name__ == "__main__":
    options = parse_args()
    
    logger.info("Démarrage de l'entraînement du détecteur d'anomalies")
    asyncio.run(train_and_save_models(options))
