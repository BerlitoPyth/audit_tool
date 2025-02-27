import asyncio
import sys
import os
import logging
from datetime import datetime
import json
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.my_fec_generator import get_my_fec_generator, MyFECGenerator
from backend.models.trained_detector import get_trained_detector
from backend.utils.json_utils import json_dump
from backend.models.schemas import AnomalyResponse

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_detector_with_generator(count: int = 1000, output_file: str = None, anomaly_rate: float = 0.05):
    """
    Génère des données avec le générateur personnalisé et les analyse avec le détecteur
    
    Args:
        count: Nombre d'écritures à générer
        output_file: Chemin où sauvegarder les résultats
        anomaly_rate: Taux d'anomalies à générer
    """
    logger.info(f"Génération de {count} écritures comptables avec un taux d'anomalie de {anomaly_rate*100}%...")
    
    # Créer une instance directe du générateur pour plus de contrôle
    generator = MyFECGenerator(
        company_name="TEST DETECTION SAS",
        start_date="2023-01-01",
        end_date="2023-12-31",
        transaction_count=count,
        anomaly_rate=anomaly_rate
    )
    
    # Générer les écritures
    entries = generator.generate_entries(count=count)
    
    # Utiliser le détecteur d'anomalies entraîné
    logger.info("Analyse des données avec le détecteur...")
    start_time = datetime.now()
    detector = get_trained_detector()
    anomalies = await detector.detect_anomalies(entries)
    end_time = datetime.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    # Compiler les résultats
    result = AnomalyResponse(
        anomalies=anomalies,
        total_count=len(anomalies),
        file_id="generator_test",
        analysis_duration_ms=duration_ms
    )
    
    # Afficher les résultats
    logger.info(f"\nRésultats de l'analyse :")
    logger.info(f"Nombre total d'écritures : {len(entries)}")
    logger.info(f"Nombre d'anomalies détectées : {len(anomalies)}")
    logger.info(f"Durée de l'analyse : {duration_ms:.2f} ms")
    
    # Sauvegarder les résultats
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json_dump(result.dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Résultats sauvegardés dans {output_file}")
    
    # Analyse des types d'anomalies
    anomaly_types = {}
    confidence_total = 0
    
    for anomaly in anomalies:
        if anomaly.type not in anomaly_types:
            anomaly_types[anomaly.type] = 0
        anomaly_types[anomaly.type] += 1
        confidence_total += anomaly.confidence_score
    
    logger.info("\nRépartition des anomalies par type :")
    for type_name, count in sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"- {type_name}: {count} anomalies ({count/len(anomalies)*100:.1f}%)")
    
    if anomalies:
        avg_confidence = confidence_total / len(anomalies)
        logger.info(f"\nConfiance moyenne des anomalies : {avg_confidence:.2f}")
    
    return result


if __name__ == "__main__":
    # Nombre d'écritures à générer
    count = 1000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    
    # Taux d'anomalies
    anomaly_rate = 0.05
    if len(sys.argv) > 2:
        anomaly_rate = float(sys.argv[2])
    
    # Fichier de sortie optionnel
    output_file = None
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    else:
        # Fichier par défaut dans le répertoire data
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data", "test_results")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    asyncio.run(test_detector_with_generator(count=count, output_file=output_file, anomaly_rate=anomaly_rate))
