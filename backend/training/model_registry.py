"""
Module de gestion du registre des modèles entraînés.
Ce module permet d'enregistrer, activer et récupérer les modèles ML.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from functools import lru_cache

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ModelRegistry:
    """Registre des modèles entraînés"""
    
    def __init__(self):
        """Initialise le registre des modèles"""
        self.models_dir = os.path.join(settings.DATA_DIR, "models")
        self.registry_file = os.path.join(self.models_dir, "registry.json")
        
        # Créer le répertoire models s'il n'existe pas
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Créer le fichier registry.json s'il n'existe pas
        if not os.path.exists(self.registry_file):
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({"models": [], "active_version": None}, f, indent=2)
    
    def register_model(self, 
                     version: str, 
                     model_files: Dict[str, str], 
                     metrics: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enregistre un nouveau modèle dans le registre
        
        Args:
            version: Version unique du modèle
            model_files: Chemins des fichiers du modèle
            metrics: Métriques d'évaluation du modèle
            metadata: Métadonnées supplémentaires
            
        Returns:
            True si l'enregistrement a réussi
        """
        try:
            # Charger le registre
            registry = self._load_registry()
            
            # Vérifier si cette version existe déjà
            if any(model["version"] == version for model in registry["models"]):
                logger.warning(f"Un modèle avec la version {version} existe déjà")
                return False
            
            # Créer l'entrée du modèle
            model_entry = {
                "version": version,
                "created_at": datetime.now().isoformat(),
                "files": model_files,
                "metrics": metrics or {},
                "metadata": metadata or {},
                "is_active": False
            }
            
            # Ajouter au registre
            registry["models"].append(model_entry)
            
            # Sauvegarder le registre
            self._save_registry(registry)
            
            logger.info(f"Modèle version {version} enregistré avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du modèle: {str(e)}", exc_info=True)
            return False
    
    def set_active_model(self, version: str) -> bool:
        """
        Active un modèle spécifique
        
        Args:
            version: Version du modèle à activer
            
        Returns:
            True si l'activation a réussi
        """
        try:
            # Charger le registre
            registry = self._load_registry()
            
            # Rechercher le modèle
            model_found = False
            
            # Désactiver tous les modèles et activer celui spécifié
            for model in registry["models"]:
                if model["version"] == version:
                    model["is_active"] = True
                    model_found = True
                else:
                    model["is_active"] = False
            
            if not model_found:
                logger.warning(f"Modèle version {version} introuvable")
                return False
            
            # Mettre à jour la version active
            registry["active_version"] = version
            
            # Sauvegarder le registre
            self._save_registry(registry)
            
            logger.info(f"Modèle version {version} activé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'activation du modèle: {str(e)}", exc_info=True)
            return False
    
    def get_active_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations sur le modèle actif
        
        Returns:
            Informations du modèle actif ou None si aucun modèle actif
        """
        try:
            # Charger le registre
            registry = self._load_registry()
            active_version = registry.get("active_version")
            
            if not active_version:
                logger.info("Aucun modèle actif défini")
                return None
            
            # Rechercher le modèle actif
            for model in registry["models"]:
                if model["version"] == active_version:
                    logger.debug(f"Modèle actif trouvé: {active_version}")
                    return model
            
            logger.warning(f"Modèle actif version {active_version} introuvable")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du modèle actif: {str(e)}", exc_info=True)
            return None
    
    def get_model_files(self, version: str) -> Optional[Dict[str, str]]:
        """
        Récupère les chemins des fichiers d'un modèle spécifique
        
        Args:
            version: Version du modèle
            
        Returns:
            Dictionnaire des chemins de fichiers ou None si non trouvé
        """
        try:
            # Charger le registre
            registry = self._load_registry()
            
            # Rechercher le modèle
            for model in registry["models"]:
                if model["version"] == version:
                    return model["files"]
            
            logger.warning(f"Modèle version {version} introuvable")
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des fichiers du modèle: {str(e)}", exc_info=True)
            return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste tous les modèles enregistrés
        
        Returns:
            Liste des informations sur tous les modèles
        """
        try:
            # Charger le registre
            registry = self._load_registry()
            
            # Retourner la liste des modèles
            return registry["models"]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la liste des modèles: {str(e)}", exc_info=True)
            return []
    
    def _load_registry(self) -> Dict[str, Any]:
        """
        Charge le registre des modèles depuis le fichier
        
        Returns:
            Contenu du registre
        """
        if not os.path.exists(self.registry_file):
            return {"models": [], "active_version": None}
            
        with open(self.registry_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_registry(self, registry: Dict[str, Any]) -> None:
        """
        Sauvegarde le registre des modèles dans le fichier
        
        Args:
            registry: Contenu du registre à sauvegarder
        """
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)


@lru_cache()
def get_model_registry() -> ModelRegistry:
    """
    Récupère l'instance unique du registre des modèles
    
    Returns:
        Instance du registre des modèles
    """
    return ModelRegistry()
