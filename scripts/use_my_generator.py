import asyncio
import logging
from datetime import datetime
import os
import sys

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.trained_detector import get_trained_detector
from backend.models.my_fec_generator import get_my_fec_generator
from backend.core.config import get_settings

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Initialisation
    settings = get_settings()
    generator = get_my_fec_generator()  # Utilisez votre générateur personnalisé
    detector = get_trained_detector()
    
    # Définir les paramètres
    generator.start_date = datetime(2023, 1, 1)
    generator.end_date = datetime(2023, 12, 31)
    generator.anomaly_rate = 0.05  # 5% d'anomalies
    generator.transaction_count = 1000
    
    # Générer des données
    logger.info("Génération des données FEC...")
    entries = generator.generate_entries(count=1000)
    
    # Sauvegarder les données générées
    output_file = os.path.join(settings.DATA_DIR, "my_generated_fec_sample.csv")
    generator.save_to_csv(entries, output_file)
    logger.info(f"Données FEC sauvegardées dans : {output_file}")
    
    # Analyser les données avec le détecteur
    logger.info("Analyse des données...")
    anomalies = await detector.detect_anomalies(entries)
    
    # Afficher les résultats
    logger.info(f"\nRésultats de l'analyse :")
    logger.info(f"Nombre total d'écritures : {len(entries)}")
    logger.info(f"Nombre d'anomalies détectées : {len(anomalies)}")
    
    # Grouper les anomalies par type
    anomaly_types = {}
    for anomaly in anomalies:
        if anomaly.type not in anomaly_types:
            anomaly_types[anomaly.type] = 0
        anomaly_types[anomaly.type] += 1
    
    logger.info("\nRépartition des anomalies par type :")
    for type_name, count in anomaly_types.items():
        logger.info(f"- {type_name}: {count} anomalies")

if __name__ == "__main__":
    asyncio.run(main())
