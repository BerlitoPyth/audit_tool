#!/usr/bin/env python
import asyncio
import sys
import os
import json
import logging
import argparse
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.append(project_dir)

from backend.services.generation_service import get_generation_service
from backend.utils.logging_utils import setup_logging

# Configurer le logging
logger = setup_logging(log_level=logging.INFO)

async def generate_and_analyze(args):
    """Génère et analyse des données FEC selon les arguments fournis"""
    try:
        # Récupérer le service
        generation_service = get_generation_service()
        
        # Préparer les options
        options = {}
        if args.start_date:
            options["start_date"] = args.start_date
        if args.end_date:
            options["end_date"] = args.end_date
        if args.company_name:
            options["company_name"] = args.company_name
        
        # Générer et analyser
        results = await generation_service.generate_and_analyze(
            count=args.count,
            anomaly_rate=args.anomaly_rate,
            options=options
        )
        
        # Afficher un résumé
        logger.info(f"\n===== Résumé de la génération =====")
        logger.info(f"ID de génération: {results['generation_id']}")
        logger.info(f"Écritures générées: {results['count']}")
        logger.info(f"Anomalies détectées: {results['anomaly_count']}")
        logger.info(f"Taux d'anomalies effectif: {results['anomaly_count'] / results['count'] * 100:.2f}%")
        logger.info(f"Durée de l'analyse: {results['duration_ms']:.2f} ms")
        logger.info(f"Fichier CSV: {results['csv_path']}")
        logger.info(f"Fichier de résultats: {results['result_path']}")
        
        # Si verbose, afficher les types d'anomalies
        if args.verbose:
            anomalies = results["analysis_result"].anomalies
            anomaly_types = {}
            
            for anomaly in anomalies:
                if anomaly.type not in anomaly_types:
                    anomaly_types[anomaly.type] = 0
                anomaly_types[anomaly.type] += 1
            
            logger.info(f"\n===== Types d'anomalies détectées =====")
            for type_name, count in sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"- {type_name}: {count} ({count/len(anomalies)*100:.1f}%)")
            
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération et l'analyse: {e}", exc_info=True)
        sys.exit(1)

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Génère et analyse des données FEC")
    
    parser.add_argument("--count", type=int, default=1000,
                        help="Nombre d'écritures à générer (défaut: 1000)")
    
    parser.add_argument("--anomaly-rate", type=float, default=0.05,
                        help="Taux d'anomalies à introduire (défaut: 0.05)")
    
    parser.add_argument("--start-date", type=str,
                        help="Date de début au format YYYY-MM-DD")
    
    parser.add_argument("--end-date", type=str,
                        help="Date de fin au format YYYY-MM-DD")
    
    parser.add_argument("--company-name", type=str,
                        help="Nom de l'entreprise")
    
    parser.add_argument("--output", type=str,
                        help="Chemin du fichier de sortie pour les résultats")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Afficher des informations détaillées")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    results = asyncio.run(generate_and_analyze(args))
    
    # Si un fichier de sortie est spécifié, enregistrer les résultats
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Résultats enregistrés dans {args.output}")
