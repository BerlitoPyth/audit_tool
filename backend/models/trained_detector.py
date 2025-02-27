"""
Module contenant le détecteur d'anomalies entraîné.
Ce module utilise les modèles de ML pour détecter les anomalies.
"""
import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from functools import lru_cache
import joblib  # Import ajouté pour résoudre l'erreur

from backend.models.schemas import Anomaly, AnomalyType
from backend.training.train_detector import AnomalyDetectorTrainer
from backend.core.config import get_settings
from backend.training.model_registry import get_model_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class TrainedDetector:
    """Détecteur d'anomalies utilisant les modèles entraînés ML"""
    
    def __init__(self, model_version: Optional[str] = None):
        """
        Initialise le détecteur avec les modèles ML entraînés
        
        Args:
            model_version: Version spécifique du modèle à charger, si None utilise le modèle actif
        """
        # Récupérer le registre de modèles
        self.model_registry = get_model_registry()
        
        # Détermine quelle version du modèle charger
        try:
            if (model_version):
                # Utiliser la version spécifiée
                model_files = self.model_registry.get_model_files(model_version)
                if not model_files:
                    raise ValueError(f"Version de modèle non trouvée: {model_version}")
                logger.info(f"Chargement du modèle version {model_version}")
            else:
                # Utiliser le modèle actif
                active_model = self.model_registry.get_active_model_info()
                if not active_model:
                    raise ValueError("Aucun modèle actif trouvé dans le registre")
                model_files = active_model["files"]
                model_version = active_model["version"]
                logger.info(f"Chargement du modèle actif, version {model_version}")
            
            # Initialiser le trainer
            self.trainer = AnomalyDetectorTrainer()
            
            # Charger les fichiers des modèles
            for model_name in ["amount", "date_patterns", "balance"]:
                model_path = model_files.get(f"{model_name}_model")
                scaler_path = model_files.get(f"{model_name}_scaler")
                
                if not model_path or not os.path.exists(model_path):
                    raise ValueError(f"Fichier de modèle manquant pour {model_name}")
                    
                if not scaler_path or not os.path.exists(scaler_path):
                    raise ValueError(f"Fichier de scaler manquant pour {model_name}")
                
                # Charger le modèle et le scaler
                self.trainer.models[model_name] = joblib.load(model_path)
                self.trainer.scalers[model_name] = joblib.load(scaler_path)
            
            # Modèle ML chargé avec succès
            self._use_ml_models = True
            self.model_version = model_version
            logger.info(f"Détecteur initialisé avec les modèles ML version {model_version}")
            
        except Exception as e:
            # En cas d'échec, utiliser le détecteur basé sur des règles
            logger.warning(f"Impossible de charger les modèles ML: {str(e)}. Utilisation du détecteur basé sur des règles.")
            self._use_ml_models = False
            self.model_version = None
            # Paramètres pour le détecteur basé sur des règles
            self.threshold_round_amount = 0.01
            self.threshold_duplicate_similarity = 0.9
            self.working_days = [0, 1, 2, 3, 4]  # 0=Lundi, 4=Vendredi
            self.working_hours = (8, 19)
            self.suspicious_round_amounts = [100, 500, 1000, 5000, 10000]
    
    async def detect_anomalies(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """
        Détecte les anomalies dans les données fournies
        
        Args:
            entries: Liste des écritures comptables à analyser
            
        Returns:
            Liste d'anomalies détectées
        """
        # Temps de début pour mesurer les performances
        start_time = datetime.now()
        
        # Ajouter un numéro de ligne pour faciliter le référencement
        for i, entry in enumerate(entries):
            entry['line_number'] = i + 1
            
        # Utiliser le détecteur ML si disponible, sinon le détecteur basé sur des règles
        if self._use_ml_models:
            anomalies = await self._detect_with_ml(entries)
        else:
            anomalies = await self._detect_with_rules(entries)
        
        # Mesurer le temps d'exécution
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Enregistrer les statistiques de détection
        self._log_detection_stats(len(entries), len(anomalies), execution_time)
        
        return anomalies
    
    def _log_detection_stats(self, num_entries: int, num_anomalies: int, execution_time: float):
        """
        Enregistre les statistiques de détection pour suivi des performances
        
        Args:
            num_entries: Nombre d'entrées analysées
            num_anomalies: Nombre d'anomalies détectées
            execution_time: Temps d'exécution en secondes
        """
        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "model_version": self.model_version,
                "method": "ml" if self._use_ml_models else "rules",
                "num_entries": num_entries,
                "num_anomalies": num_anomalies,
                "anomaly_rate": num_anomalies / num_entries if num_entries > 0 else 0,
                "execution_time": execution_time,
                "entries_per_second": num_entries / execution_time if execution_time > 0 else 0
            }
            
            # Log les statistiques
            logger.info(
                f"Détection terminée: {stats['num_anomalies']}/{stats['num_entries']} anomalies "
                f"({stats['anomaly_rate']:.2%}) en {stats['execution_time']:.2f}s "
                f"({stats['entries_per_second']:.1f} entrées/s) avec {'ML' if self._use_ml_models else 'règles'}"
            )
            
            # Sauvegarder les statistiques dans un fichier pour analyse ultérieure
            stats_dir = os.path.join(settings.DATA_DIR, "stats")
            os.makedirs(stats_dir, exist_ok=True)
            
            stats_file = os.path.join(stats_dir, "detection_stats.jsonl")
            with open(stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(stats) + "\n")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des statistiques: {str(e)}")
    
    async def _detect_with_ml(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """Détecte les anomalies en utilisant les modèles ML"""
        try:
            # Extraction des caractéristiques
            features = self.trainer._extract_features(entries)
            anomalies = []
            
            # Détection pour chaque type d'anomalie
            for name, model in self.trainer.models.items():
                # Normalisation
                X = self.trainer.scalers[name].transform(features[name])
                # Prédiction
                predictions = model.predict(X)
                scores = model.score_samples(X)
                
                # Identifier les anomalies
                for idx, (is_anomaly, score) in enumerate(zip(predictions, scores)):
                    if is_anomaly == -1:  # -1 indique une anomalie
                        entry = entries[idx]
                        
                        # Déterminer le type d'anomalie
                        if name == "amount":
                            anomaly_type = AnomalyType.SUSPICIOUS_PATTERN
                            description = "Montant suspect détecté par ML"
                        elif name == "date_patterns":
                            anomaly_type = AnomalyType.DATE_INCONSISTENCY
                            description = "Schéma temporel inhabituel détecté par ML"
                        else:  # balance
                            anomaly_type = AnomalyType.BALANCE_MISMATCH
                            description = "Déséquilibre inhabituel détecté par ML"
                        
                        # Convertir le score en confiance (plus le score est bas, plus l'anomalie est forte)
                        confidence = 1.0 - np.exp(score)
                        
                        # Créer l'anomalie
                        anomaly = Anomaly(
                            id=str(uuid.uuid4()),
                            type=anomaly_type,
                            description=description,
                            confidence_score=confidence,  
                            line_numbers=[idx + 1],
                            related_data={
                                "model": name,
                                "model_version": self.model_version,
                                "score": float(score),
                                "entry_preview": {
                                    k: str(v) for k, v in entry.items() 
                                    if k in ['journal_code', 'compte_num', 'ecriture_lib']
                                }
                            },
                            detected_at=datetime.now()
                        )
                        anomalies.append(anomaly)
            
            logger.info(f"Détection ML terminée: {len(anomalies)} anomalies trouvées")
            return anomalies
            
        except Exception as e:
            # En cas d'erreur avec le ML, revenir aux règles
            logger.error(f"Erreur lors de la détection ML: {str(e)}. Utilisation du détecteur basé sur des règles.")
            return await self._detect_with_rules(entries)
    
    async def _detect_with_rules(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """Analyse les entrées et détecte les anomalies avec des règles prédéfinies"""
        anomalies = []
        
        # Vérifications individuelles sur chaque entrée
        for entry in entries:
            # Vérification du montant
            anomaly = self._check_round_amount(entry)
            if anomaly:
                anomalies.append(anomaly)
                
            # Vérification de la date
            anomaly = self._check_weekend_transaction(entry)
            if anomaly:
                anomalies.append(anomaly)
                
            # Vérification des données manquantes
            anomaly = self._check_missing_data(entry)
            if anomaly:
                anomalies.append(anomaly)
        
        # Vérifications globales sur l'ensemble des entrées
        anomalies.extend(self._check_duplicates(entries))
        anomalies.extend(self._check_balance_mismatch(entries))
        
        logger.info(f"Détection basée sur des règles terminée: {len(anomalies)} anomalies trouvées")
        return anomalies
    
    def _check_round_amount(self, entry: Dict[str, Any]) -> Optional[Anomaly]:
        """Vérifie si le montant est suspicieusement rond"""
        amount = max(float(entry.get('debit_montant', 0)), float(entry.get('credit_montant', 0)))
        
        # Vérifier si le montant est exactement un montant rond
        is_exact_round = any(abs(amount - round_amount) < 0.01 for round_amount in self.suspicious_round_amounts)
        
        # Vérifier si le montant a une partie décimale très proche de zéro ou d'un entier
        decimal_part = amount - int(amount)
        is_almost_round = decimal_part < self.threshold_round_amount or decimal_part > (1 - self.threshold_round_amount)
        
        if (is_exact_round or is_almost_round) and amount >= 1000:
            return Anomaly(
                id=str(uuid.uuid4()),
                type=AnomalyType.SUSPICIOUS_PATTERN,
                description=f"Montant suspicieusement rond: {amount}",
                confidence_score=0.8 if is_exact_round else 0.6,
                line_numbers=[entry.get('line_number', 0)],
                related_data={
                    "amount": amount,
                    "is_exact_round": is_exact_round,
                    "journal_code": entry.get('journal_code', ''),
                    "ecriture_lib": entry.get('ecriture_lib', '')
                },
                detected_at=datetime.now()
            )
        return None
    
    def _check_weekend_transaction(self, entry: Dict[str, Any]) -> Optional[Anomaly]:
        """Vérifie si la transaction est faite un weekend ou hors heures de bureau"""
        if 'ecr_date' not in entry:
            return None
        
        try:
            # Convertir la date en datetime si c'est une chaîne
            ecr_date = entry['ecr_date']
            if isinstance(ecr_date, str):
                try:
                    ecr_date = datetime.fromisoformat(ecr_date)
                except ValueError:
                    # Essayer un autre format courant dans les FEC
                    ecr_date = datetime.strptime(ecr_date, "%Y%m%d")
            
            # Vérifier si c'est un weekend (5=samedi, 6=dimanche)
            weekday = ecr_date.weekday()
            is_weekend = weekday not in self.working_days
            
            # Vérifier si c'est hors heures de bureau
            hour = ecr_date.hour
            is_outside_hours = hour < self.working_hours[0] or hour > self.working_hours[1]
            
            if is_weekend:
                return Anomaly(
                    id=str(uuid.uuid4()),
                    type=AnomalyType.DATE_INCONSISTENCY,
                    description=f"Transaction effectuée un weekend ({['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][weekday]})",
                    confidence_score=0.9,
                    line_numbers=[entry.get('line_number', 0)],
                    related_data={
                        "date": ecr_date.isoformat(),
                        "weekday": weekday,
                        "journal_code": entry.get('journal_code', ''),
                        "ecriture_lib": entry.get('ecriture_lib', '')
                    },
                    detected_at=datetime.now()
                )
            
            if is_outside_hours and hour != 0:  # Ignorer minuit qui peut être une valeur par défaut
                return Anomaly(
                    id=str(uuid.uuid4()),
                    type=AnomalyType.DATE_INCONSISTENCY,
                    description=f"Transaction effectuée en dehors des heures de bureau ({hour}h)",
                    confidence_score=0.7,
                    line_numbers=[entry.get('line_number', 0)],
                    related_data={
                        "date": ecr_date.isoformat(),
                        "hour": hour,
                        "journal_code": entry.get('journal_code', ''),
                        "ecriture_lib": entry.get('ecriture_lib', '')
                    },
                    detected_at=datetime.now()
                )
                
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification de la date: {str(e)}")
        
        return None
    
    def _check_duplicates(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """Détecte les écritures potentiellement dupliquées"""
        anomalies = []
        
        # Créer une empreinte simplifiée pour chaque entrée pour comparer
        entries_with_signature = []
        for idx, entry in enumerate(entries):
            # Simplifier la date pour la comparaison
            date_str = ""
            if 'ecr_date' in entry:
                date = entry['ecr_date']
                if isinstance(date, datetime):
                    date_str = date.strftime('%Y%m%d')
                else:
                    date_str = str(date)[:8]  # Obtenir les 8 premiers caractères
            
            # Créer une signature pour cette entrée
            signature = {
                'amount': max(float(entry.get('debit_montant', 0)), float(entry.get('credit_montant', 0))),
                'date': date_str,
                'compte_num': entry.get('compte_num', ''),
                'journal_code': entry.get('journal_code', ''),
                'ecriture_lib': entry.get('ecriture_lib', '')[:20]  # Premiers 20 caractères
            }
            entries_with_signature.append((idx, entry, signature))
        
        # Comparer les signatures pour détecter les doublons potentiels
        for i in range(len(entries_with_signature)):
            idx1, entry1, sig1 = entries_with_signature[i]
            
            for j in range(i + 1, min(i + 100, len(entries_with_signature))):  # Limite la recherche pour des raisons de performance
                idx2, entry2, sig2 = entries_with_signature[j]
                
                # Calculer la similarité entre les deux signatures
                similarity_score = 0
                
                # Même montant exact
                if abs(sig1['amount'] - sig2['amount']) < 0.01:
                    similarity_score += 0.5
                
                # Même date
                if sig1['date'] == sig2['date']:
                    similarity_score += 0.2
                
                # Même compte
                if sig1['compte_num'] == sig2['compte_num']:
                    similarity_score += 0.15
                
                # Même journal
                if sig1['journal_code'] == sig2['journal_code']:
                    similarity_score += 0.1
                
                # Libellé similaire
                if sig1['ecriture_lib'] == sig2['ecriture_lib']:
                    similarity_score += 0.05
                
                # Si la similarité est supérieure au seuil, c'est un doublon potentiel
                if similarity_score >= self.threshold_duplicate_similarity:
                    anomalies.append(Anomaly(
                        id=str(uuid.uuid4()),
                        type=AnomalyType.DUPLICATE_ENTRY,
                        description=f"Écriture potentiellement dupliquée",
                        confidence_score=similarity_score,
                        line_numbers=[idx1 + 1, idx2 + 1],  # +1 car les lignes sont indexées à partir de 1
                        related_data={
                            "first_entry": {
                                "line": idx1 + 1,
                                "compte": entry1.get('compte_num', ''),
                                "date": sig1['date'],
                                "montant": sig1['amount'],
                                "libelle": entry1.get('ecriture_lib', '')
                            },
                            "second_entry": {
                                "line": idx2 + 1,
                                "compte": entry2.get('compte_num', ''),
                                "date": sig2['date'],
                                "montant": sig2['amount'],
                                "libelle": entry2.get('ecriture_lib', '')
                            },
                            "similarity_score": similarity_score
                        },
                        detected_at=datetime.now()
                    ))
        
        return anomalies
    
    def _check_balance_mismatch(self, entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """Vérifie l'équilibre des écritures comptables"""
        anomalies = []
        
        # Regrouper les entrées par numéro d'écriture
        entries_by_ecr_num = {}
        for idx, entry in enumerate(entries):
            ecr_num = entry.get('ecr_num', None)
            if not ecr_num:
                continue
                
            if ecr_num not in entries_by_ecr_num:
                entries_by_ecr_num[ecr_num] = []
            entries_by_ecr_num[ecr_num].append((idx, entry))
        
        # Vérifier l'équilibre pour chaque écriture
        for ecr_num, entries_with_idx in entries_by_ecr_num.items():
            total_debit = sum(float(entry.get('debit_montant', 0)) for _, entry in entries_with_idx)
            total_credit = sum(float(entry.get('credit_montant', 0)) for _, entry in entries_with_idx)
            
            # Calculer le déséquilibre
            diff = abs(total_debit - total_credit)
            
            # Si le déséquilibre est significatif
            if diff > 0.01:  # Tolérance pour les erreurs d'arrondi
                line_numbers = [idx + 1 for idx, _ in entries_with_idx]
                anomalies.append(Anomaly(
                    id=str(uuid.uuid4()),
                    type=AnomalyType.BALANCE_MISMATCH,
                    description=f"Déséquilibre entre débit et crédit: {diff:.2f}",
                    confidence_score=min(0.95, 0.5 + diff / 100),  # Plus le déséquilibre est grand, plus la confiance est élevée
                    line_numbers=line_numbers,
                    related_data={
                        "ecr_num": ecr_num,
                        "total_debit": total_debit,
                        "total_credit": total_credit,
                        "difference": diff,
                        "entries_count": len(entries_with_idx)
                    },
                    detected_at=datetime.now()
                ))
        
        return anomalies
    
    def _check_missing_data(self, entry: Dict[str, Any]) -> Optional[Anomaly]:
        """Vérifie les données manquantes dans les champs obligatoires"""
        required_fields = ['ecr_date', 'compte_num', 'ecriture_lib']
        missing_fields = [field for field in required_fields if field not in entry or not entry[field]]
        
        if missing_fields:
            return Anomaly(
                id=str(uuid.uuid4()),
                type=AnomalyType.MISSING_DATA,
                description=f"Données manquantes dans {len(missing_fields)} champ(s) obligatoire(s)",
                confidence_score=0.95,
                line_numbers=[entry.get('line_number', 0)],
                related_data={
                    "missing_fields": missing_fields,
                    "entry_preview": {k: v for k, v in entry.items() if k in ['compte_num', 'journal_code', 'ecriture_lib']}
                },
                detected_at=datetime.now()
            )
        return None


# Instance singleton du détecteur
_detector = None

def get_trained_detector():
    """Récupère l'instance unique du détecteur"""
    global _detector
    if (_detector is None):
        _detector = TrainedDetector()
    return _detector