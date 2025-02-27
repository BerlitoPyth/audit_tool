"""
Module pour la détection d'anomalies dans les données financières.
Ce module sert de façade pour les différents détecteurs spécifiques.
"""
import logging
from typing import List, Dict, Any, Optional, Union
import asyncio
from datetime import datetime
from functools import lru_cache

from backend.models.schemas import Anomaly, AnomalyType
from backend.models.trained_detector import get_trained_detector, TrainedDetector
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AnomalyDetector:
    """
    Détecteur d'anomalies principal qui coordonne les différents types de détection
    et consolide les résultats.
    """
    
    def __init__(self, use_ml: bool = True):
        """
        Initialise le détecteur d'anomalies
        
        Args:
            use_ml: Si True, utilise les modèles ML si disponibles
        """
        self.use_ml = use_ml
        self._ml_detector = get_trained_detector() if use_ml else None
    
    async def detect_anomalies(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """
        Détecte les anomalies dans les données fournies
        
        Args:
            entries: Liste des écritures comptables à analyser
            
        Returns:
            Liste d'anomalies détectées
        """
        if not entries:
            logger.warning("Aucune entrée à analyser pour la détection d'anomalies")
            return []
        
        logger.info(f"Début de la détection d'anomalies sur {len(entries)} écritures")
        start_time = datetime.now()
        
        # Utiliser le détecteur ML si disponible
        if self.use_ml and self._ml_detector and self._ml_detector._use_ml_models:
            logger.info("Utilisation du détecteur d'anomalies basé sur ML")
            anomalies = await self._ml_detector.detect_anomalies(entries)
        else:
            logger.info("Utilisation du détecteur d'anomalies basé sur des règles")
            anomalies = await self._detect_with_rules(entries)
        
        # Ajouter des métadonnées et consolider les résultats
        result = await self._consolidate_anomalies(anomalies)
        
        # Calculer la durée
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Détection terminée: {len(result)} anomalies trouvées en {duration:.2f} secondes")
        
        return result
    
    async def _detect_with_rules(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """
        Méthode de détection basée sur des règles (fallback si ML non disponible)
        
        Args:
            entries: Liste des écritures à analyser
            
        Returns:
            Liste des anomalies détectées
        """
        # Utiliser l'implémentation du TrainedDetector pour les règles
        detector = self._ml_detector or TrainedDetector()
        return await detector.detect_anomalies(entries)
    
    async def _consolidate_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """
        Consolide et filtre les anomalies détectées
        
        Args:
            anomalies: Liste des anomalies brutes détectées
            
        Returns:
            Liste des anomalies consolidées
        """
        # Filtrer les anomalies de faible confiance
        threshold = 0.3  # Seuil minimal de confiance
        filtered = [a for a in anomalies if a.confidence_score >= threshold]
        
        # Trier par score de confiance (décroissant)
        sorted_anomalies = sorted(filtered, key=lambda a: a.confidence_score, reverse=True)
        
        # Limiter le nombre total d'anomalies remontées
        max_anomalies = 100
        if len(sorted_anomalies) > max_anomalies:
            logger.info(f"Limitation à {max_anomalies} anomalies sur {len(sorted_anomalies)} détectées")
            return sorted_anomalies[:max_anomalies]
        
        return sorted_anomalies


# Instance singleton
_detector = None

def get_anomaly_detector(use_ml: bool = True) -> AnomalyDetector:
    """
    Récupère l'instance singleton du détecteur d'anomalies
    
    Args:
        use_ml: Si True, utilise les modèles ML si disponibles
        
    Returns:
        Instance du détecteur d'anomalies
    """
    global _detector
    if _detector is None:
        _detector = AnomalyDetector(use_ml=use_ml)
    return _detector
