"""Utilitaires pour manipuler des données JSON"""
import json
from datetime import datetime, date
import logging
from typing import Any
from decimal import Decimal
from uuid import UUID

logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les types spéciaux"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        try:
            # Pour les objets Pydantic ou autres avec une méthode dict()
            if hasattr(obj, 'dict'):
                return obj.dict()
            # Pour les autres objets qui peuvent être convertis en dict
            return dict(obj)
        except Exception:
            # Retour à l'encodage par défaut
            return super().default(obj)

def json_serial(obj):
    """Convertisseur JSON pour les types non sérialisables par défaut"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} non sérialisable")

def json_dumps(obj: Any, **kwargs) -> str:
    """Sérialise un objet en JSON en utilisant l'encodeur personnalisé"""
    kwargs.setdefault('default', json_serial)
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)

def json_dump(obj: Any, fp, **kwargs) -> None:
    """Écrit un objet en JSON dans un fichier en utilisant l'encodeur personnalisé"""
    kwargs.setdefault('default', json_serial)
    json.dump(obj, fp, cls=CustomJSONEncoder, **kwargs)

def json_load(fp, **kwargs):
    """
    Charge un objet JSON depuis un fichier
    
    Args:
        fp: Fichier ou descripteur de fichier
        **kwargs: Arguments supplémentaires pour json.load
        
    Returns:
        Objet Python
    """
    return json.load(fp, **kwargs)

def json_loads(s, **kwargs):
    """
    Parse une chaîne JSON
    
    Args:
        s: Chaîne JSON
        **kwargs: Arguments supplémentaires pour json.loads
        
    Returns:
        Objet Python
    """
    return json.loads(s, **kwargs)
