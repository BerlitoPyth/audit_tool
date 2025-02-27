import asyncio
import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.my_fec_generator import get_my_fec_generator
from backend.models.trained_detector import get_trained_detector
from backend.utils.json_utils import json_dump
from backend.models.schemas import AnomalyResponse

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def analyze_custom_data(count: int = 1000, output_file: str = None):
    """Génère et analyse des données personnalisées"""
    logger.info(f"Génération de {count} écritures comptables...")
    
    # Utiliser votre générateur personnalisé
    generator = get_my_fec_generator()
    entries = generator.generate_entries(count=count)
    
    # Utiliser le détecteur d'anomalies entraîné
    logger.info("Analyse des données...")
    detector = get_trained_detector()
    anomalies = await detector.detect_anomalies(entries)
    
    # Créer la réponse d'analyse
    result = AnomalyResponse(
        anomalies=anomalies,
        total_count=len(anomalies),
        file_id="custom_analysis",
        analysis_duration_ms=0
    )
    
    # Afficher les résultats
    logger.info(f"\nRésultats de l'analyse :")
    logger.info(f"Nombre total d'écritures : {len(entries)}")
    logger.info(f"Nombre d'anomalies détectées : {len(anomalies)}")
    
    # Sauvegarder les résultats si un fichier de sortie est spécifié
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json_dump(result.dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Résultats sauvegardés dans {output_file}")
    
    # Analyse des types d'anomalies
    anomaly_types = {}
    for anomaly in anomalies:
        if anomaly.type not in anomaly_types:
            anomaly_types[anomaly.type] = 0
        anomaly_types[anomaly.type] += 1
    
    logger.info("\nRépartition des anomalies par type :")
    for type_name, count in anomaly_types.items():
        logger.info(f"- {type_name}: {count} anomalies")
    
    return result


if __name__ == "__main__":
    # Nombre d'écritures à générer
    count = 1000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    
    # Fichier de sortie optionnel
    output_file = None
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    asyncio.run(analyze_custom_data(count=count, output_file=output_file))
