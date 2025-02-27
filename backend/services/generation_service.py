"""Service pour la génération des données FEC"""
import os
import json
import logging
import asyncio
from datetime import datetime
import uuid
import time
from typing import Dict, Any, Optional, List
from functools import lru_cache

from backend.core.config import get_settings
from backend.models.my_fec_generator import MyFECGenerator
from backend.models.anomaly_detector import get_anomaly_detector

logger = logging.getLogger(__name__)
settings = get_settings()


class GenerationService:
    """Service pour la génération de données FEC"""
    
    def __init__(self):
        """Initialise le service de génération"""
        self.data_dir = settings.DATA_DIR
        self.generation_dir = os.path.join(self.data_dir, "generated")
        os.makedirs(self.generation_dir, exist_ok=True)
    
    async def generate_and_analyze(self, 
                          count: int = 1000, 
                          anomaly_rate: float = 0.05, 
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Génère un jeu de données FEC et analyse les anomalies
        
        Args:
            count: Nombre d'écritures à générer
            anomaly_rate: Taux d'anomalies à introduire (0-1)
            options: Options supplémentaires pour la génération
            
        Returns:
            Dictionnaire des résultats
        """
        options = options or {}
        start_time = time.time()
        generation_id = str(uuid.uuid4())
        
        try:
            # Configurer le générateur
            generator_params = {
                "company_name": options.get("company_name", f"COMPANY_{generation_id[:8]}"),
                "start_date": options.get("start_date", "2023-01-01"),
                "end_date": options.get("end_date", "2023-12-31"),
                "transaction_count": count,
                "anomaly_rate": anomaly_rate
            }
            
            # Créer le générateur
            generator = MyFECGenerator(**generator_params)
            
            # Générer les données
            logger.info(f"Génération de {count} écritures avec {anomaly_rate:.1%} d'anomalies")
            entries = generator.generate_entries()
            
            # Sauvegarder les données générées au format CSV
            csv_path = os.path.join(self.generation_dir, f"generated_{generation_id}.csv")
            self._save_as_csv(entries, csv_path)
            
            # Analyser les anomalies
            detector = get_anomaly_detector()
            anomalies = await detector.detect_anomalies(entries)
            
            # Durée totale
            duration_ms = (time.time() - start_time) * 1000
            
            # Préparer les résultats
            results = {
                "generation_id": generation_id,
                "count": len(entries),
                "anomaly_count": len(anomalies),
                "anomaly_rate": anomaly_rate,
                "csv_path": csv_path,
                "duration_ms": duration_ms,
                "generated_at": datetime.now().isoformat(),
                "params": generator_params,
                "anomalies": [anomaly.model_dump() for anomaly in anomalies]  # Correction ici: model_dump() au lieu de dict()
            }
            
            # Sauvegarder les résultats
            result_path = os.path.join(self.generation_dir, f"results_{generation_id}.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=self._json_serializer)
            
            results["result_path"] = result_path
            
            logger.info(f"Génération et analyse terminées: {len(anomalies)} anomalies trouvées")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération et analyse: {str(e)}", exc_info=True)
            raise
    
    def _save_as_csv(self, entries: List[Dict[str, Any]], file_path: str) -> None:
        """
        Sauvegarde les entrées au format CSV
        
        Args:
            entries: Liste des écritures à sauvegarder
            file_path: Chemin du fichier de sortie
        """
        import pandas as pd
        
        # Convertir en DataFrame
        df = pd.DataFrame(entries)
        
        # Sauvegarder au format CSV avec pipe comme séparateur (format FEC)
        df.to_csv(file_path, sep='|', index=False, encoding='utf-8')
        
        logger.info(f"Données sauvegardées dans {file_path}")
    
    def _json_serializer(self, obj):
        """Fonction pour sérialiser les objets non JSON-sérialisables"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)


@lru_cache()
def get_generation_service() -> GenerationService:
    """
    Récupère l'instance unique du service de génération
    
    Returns:
        Instance du service de génération
    """
    return GenerationService()
