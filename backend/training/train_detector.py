"""
Module d'entraînement pour les détecteurs d'anomalies.
Permet d'entraîner des modèles de machine learning pour détecter différents types d'anomalies.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class AnomalyDetectorTrainer:
    """Classe pour entraîner des modèles de détection d'anomalies"""
    
    def __init__(self):
        """Initialise l'entraîneur de modèles"""
        self.models = {}
        self.scalers = {}
        self.feature_names = {}
    
    def train(self, entries: List[Dict[str, Any]]) -> None:
        """
        Entraîne les modèles de détection d'anomalies
        
        Args:
            entries: Liste des écritures comptables pour l'entraînement
        """
        if not entries:
            raise ValueError("Aucune donnée fournie pour l'entraînement")
        
        logger.info(f"Début de l'entraînement sur {len(entries)} écritures")
        
        # Extraction des caractéristiques
        features = self._extract_features(entries)
        
        # Pour chaque type de caractéristiques, entraîner un modèle spécifique
        for name, X in features.items():
            # Normalisation des données
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Entraînement du modèle Isolation Forest
            model = IsolationForest(
                n_estimators=100,
                max_samples='auto',
                contamination=0.05,  # Estimation du taux d'anomalies
                random_state=42,
                n_jobs=-1  # Utiliser tous les cœurs disponibles
            )
            
            # Entraînement
            logger.info(f"Entraînement du modèle '{name}' sur {len(X)} échantillons")
            model.fit(X_scaled)
            
            # Sauvegarde du modèle et du scaler
            self.models[name] = model
            self.scalers[name] = scaler
            self.feature_names[name] = list(X.columns) if hasattr(X, 'columns') else []
            
        logger.info(f"Entraînement terminé: {len(self.models)} modèles entraînés")
    
    def _extract_features(self, entries: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """
        Extrait les caractéristiques pertinentes des écritures comptables.
        Chaque type de caractéristiques sera utilisé pour un modèle spécifique.
        
        Args:
            entries: Liste des écritures comptables
            
        Returns:
            Dictionnaire de matrices de caractéristiques
        """
        # Initialisation des listes pour stocker les caractéristiques
        amount_features = []
        date_features = []
        balance_features = []
        
        # Pour chaque écriture, extraire les caractéristiques
        for entry in entries:
            # --- Caractéristiques liées aux montants ---
            debit = float(entry.get('debit_montant', 0))
            credit = float(entry.get('credit_montant', 0))
            amount = max(debit, credit)
            
            # Caractéristiques dérivées
            amount_log = np.log1p(amount) if amount > 0 else 0  # Log pour gérer les grandes variations
            amount_round = amount % 1  # Partie décimale (0 pour des montants ronds)
            amount_mod10 = amount % 10  # Modulo 10 (pour détecter les arrondis)
            amount_mod100 = amount % 100
            
            # Ajouter aux caractéristiques de montant
            amount_features.append([
                amount,
                amount_log,
                amount_round,
                amount_mod10,
                amount_mod100
            ])
            
            # --- Caractéristiques liées aux dates ---
            # Gérer différents formats de date (ISO et %Y%m%d)
            try:
                date_str = entry.get('ecr_date', '20240101')
                try:
                    # Essayer d'abord de parser comme date ISO
                    if isinstance(date_str, str) and 'T' in date_str:
                        date = datetime.fromisoformat(date_str)
                    else:
                        # Sinon essayer le format %Y%m%d
                        date = datetime.strptime(date_str, '%Y%m%d')
                except ValueError:
                    # Si les deux échouent, utiliser la date par défaut
                    date = datetime.now()
                
                # Extraire les informations temporelles
                weekday = date.weekday()  # 0=Lundi, 6=Dimanche
                day = date.day
                month = date.month
                hour = date.hour
                minute = date.minute
                is_weekend = 1 if weekday >= 5 else 0  # 1 pour weekend
                is_business_hours = 1 if (8 <= hour <= 18) else 0  # 1 pour heures de bureau
                
                # Ajouter aux caractéristiques de date
                date_features.append([
                    weekday,
                    day,
                    month,
                    hour,
                    minute,
                    is_weekend,
                    is_business_hours
                ])
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des caractéristiques de date: {str(e)}")
                # En cas d'erreur, utiliser des valeurs par défaut
                date_features.append([2, 15, 6, 12, 0, 0, 1])  # Valeurs neutres
            
            # --- Caractéristiques liées au solde ---
            # Analyser le compte
            account_num = entry.get('compte_num', '')
            account_class = int(account_num[0]) if account_num and account_num[0].isdigit() else 0
            
            # Indicateurs pour les types de comptes
            is_asset = 1 if account_class in [1, 2, 3] else 0  # Classes 1,2,3 = actifs
            is_liability = 1 if account_class in [4, 5] else 0  # Classes 4,5 = passifs
            is_expense = 1 if account_class == 6 else 0  # Classe 6 = charges
            is_revenue = 1 if account_class == 7 else 0  # Classe 7 = produits
            
            # Ajouter aux caractéristiques de solde
            balance_features.append([
                debit - credit,  # Différence
                debit + credit,  # Total
                account_class,
                is_asset,
                is_liability,
                is_expense,
                is_revenue
            ])
        
        # Convertir en arrays numpy
        amount_array = np.array(amount_features)
        date_array = np.array(date_features)
        balance_array = np.array(balance_features)
        
        # Convertir en DataFrame pour garder les noms des caractéristiques
        amount_df = pd.DataFrame(amount_array, columns=[
            'amount', 'amount_log', 'amount_round', 'amount_mod10', 'amount_mod100'
        ])
        
        date_df = pd.DataFrame(date_array, columns=[
            'weekday', 'day', 'month', 'hour', 'minute', 'is_weekend', 'is_business_hours'
        ])
        
        balance_df = pd.DataFrame(balance_array, columns=[
            'balance_diff', 'total_amount', 'account_class', 
            'is_asset', 'is_liability', 'is_expense', 'is_revenue'
        ])
        
        return {
            'amount': amount_df,
            'date_patterns': date_df,
            'balance': balance_df
        }
