import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models.my_fec_generator import get_my_fec_generator
from backend.utils.json_utils import json_dump

logger = logging.getLogger(__name__)

class GeneratorAdapter:
    """
    Adaptateur pour le générateur FEC personnalisé.
    Cette classe s'assure que le générateur FEC est compatible avec l'interface du système.
    """
    
    def __init__(self):
        self.generator = get_my_fec_generator()
        logger.info("GeneratorAdapter initialisé avec le générateur FEC personnalisé")
    
    async def generate_entries(self, count: int = 1000, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Génère des écritures comptables en utilisant le générateur personnalisé
        
        Args:
            count: Nombre d'écritures à générer
            options: Options supplémentaires pour la génération
            
        Returns:
            Liste des écritures générées
        """
        options = options or {}
        
        # Configurer le générateur avec les options fournies
        self._configure_generator(options)
        
        # Générer les écritures
        logger.info(f"Génération de {count} écritures comptables")
        entries = self.generator.generate_entries(count=count)
        logger.info(f"{len(entries)} écritures générées")
        
        # Permet d'utiliser la fonction dans un contexte asynchrone
        await asyncio.sleep(0)
        
        return entries
    
    def _configure_generator(self, options: Dict[str, Any]) -> None:
        """Configure le générateur avec les options fournies"""
        # Définir la période
        if "start_date" in options:
            self.generator.start_date = self._parse_date(options["start_date"])
        
        if "end_date" in options:
            self.generator.end_date = self._parse_date(options["end_date"])
        
        # Taux d'anomalies
        if "anomaly_rate" in options:
            self.generator.anomaly_rate = float(options["anomaly_rate"])
        
        # Informations sur l'entreprise
        if "company_name" in options:
            self.generator.company_name = options["company_name"]
        
        if "siren" in options:
            self.generator.siren = options["siren"]
    
    def _parse_date(self, date_value):
        """Convertit une chaîne de date en objet datetime"""
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Format de date invalide: {date_value}, utilisation de la valeur par défaut")
        return date_value

    async def save_to_file(self, entries: List[Dict[str, Any]], output_path: str) -> str:
        """
        Sauvegarde les écritures générées dans un fichier
        
        Args:
            entries: Liste des écritures à sauvegarder
            output_path: Chemin du fichier de sortie
            
        Returns:
            Chemin du fichier créé
        """
        # Utiliser la méthode de sauvegarde du générateur
        return self.generator.save_to_csv(entries, output_path)

# Singleton pour accéder à l'adaptateur
_generator_adapter = None

def get_generator_adapter():
    """Renvoie une instance singleton de l'adaptateur de générateur"""
    global _generator_adapter
    if _generator_adapter is None:
        _generator_adapter = GeneratorAdapter()
    return _generator_adapter
