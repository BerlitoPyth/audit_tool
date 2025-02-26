import logging
import os
import json
import uuid
import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import asyncio

from backend.models.schemas import Anomaly, AnomalyType
from backend.models.fec_generator import FECGenerator, get_fec_generator
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AnomalyDetector:
    """
    Détecteur d'anomalies pour les fichiers FEC.
    Utilise des règles métier et des analyses statistiques pour détecter les anomalies.
    """
    
    def __init__(self, fec_generator: FECGenerator = None):
        """
        Initialise le détecteur d'anomalies.
        
        Args:
            fec_generator: Optionnel, un générateur FEC pour l'enrichissement de données
        """
        self.fec_generator = fec_generator
        self.models_dir = settings.TRAINED_MODELS_DIR
        
        # Charger des règles métier et des seuils
        self.rules = self._load_rules()
        
        # Indicateur si le modèle est chargé
        self.model_loaded = False
        
        # Statistiques de référence (pourraient être chargées à partir d'un fichier)
        self.reference_stats = {
            "average_transaction_amount": 1000.0,
            "std_transaction_amount": 500.0,
            "average_transactions_per_day": 50,
            "max_debit_credit_ratio": 1.1,  # Ratio maximal entre débit et crédit
        }
    
    def _load_rules(self) -> Dict[str, Any]:
        """Charge les règles de détection d'anomalies"""
        # Règles par défaut (pourraient être chargées à partir d'un fichier de configuration)
        return {
            "balance_threshold": 0.01,  # Seuil d'écart pour le déséquilibre débit/crédit
            "duplicate_threshold": 0.95,  # Similarité pour considérer des entrées comme duplicates
            "suspicious_patterns": [
                {"pattern": "ADJUST", "confidence": 0.7},
                {"pattern": "CORRECTION", "confidence": 0.6},
                {"pattern": "MANUAL", "confidence": 0.5},
            ],
            "amount_outlier_zscore": 3.0,  # Z-score pour considérer un montant comme aberrant
            "weekend_activity_score": 0.8,  # Score de confiance pour l'activité le weekend
        }
    
    async def load_model(self) -> bool:
        """Charge le modèle de détection d'anomalies s'il existe"""
        model_path = os.path.join(self.models_dir, "anomaly_detector_model.json")
        
        if os.path.exists(model_path):
            try:
                with open(model_path, "r") as f:
                    model_data = json.load(f)
                
                # Mise à jour des statistiques de référence
                if "reference_stats" in model_data:
                    self.reference_stats = model_data["reference_stats"]
                
                # Mise à jour des règles
                if "rules" in model_data:
                    self.rules = model_data["rules"]
                
                self.model_loaded = True
                logger.info("Modèle de détection d'anomalies chargé avec succès")
                return True
                
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
                return False
        else:
            logger.warning("Aucun modèle de détection d'anomalies trouvé, utilisation des règles par défaut")
            return False
    
    async def save_model(self) -> bool:
        """Sauvegarde le modèle de détection d'anomalies"""
        model_path = os.path.join(self.models_dir, "anomaly_detector_model.json")
        
        try:
            model_data = {
                "reference_stats": self.reference_stats,
                "rules": self.rules,
                "last_updated": datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            with open(model_path, "w") as f:
                json.dump(model_data, f, indent=2)
            
            logger.info("Modèle de détection d'anomalies sauvegardé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du modèle: {str(e)}")
            return False
    
    async def train_model(self, fec_datasets: List[Dict[str, Any]]) -> bool:
        """
        Entraîne ou met à jour le modèle sur base de données FEC.
        
        Args:
            fec_datasets: Liste de jeux de données FEC pour l'entraînement
        
        Returns:
            bool: True si l'entraînement a réussi, False sinon
        """
        if not fec_datasets:
            logger.warning("Aucune donnée fournie pour l'entraînement")
            return False
        
        try:
            # Convertir en DataFrame pour l'analyse
            combined_data = []
            for dataset in fec_datasets:
                combined_data.extend(dataset)
            
            df = pd.DataFrame(combined_data)
            
            # Calculer de nouvelles statistiques de référence
            debit_sum = df["Debit"].sum() if "Debit" in df.columns else 0
            credit_sum = df["Credit"].sum() if "Credit" in df.columns else 0
            
            # Mettre à jour les statistiques de référence
            if "Debit" in df.columns and "Credit" in df.columns:
                total_amount = df["Debit"].sum() + df["Credit"].sum()
                transaction_count = len(df)
                
                if transaction_count > 0:
                    self.reference_stats["average_transaction_amount"] = total_amount / transaction_count
                    self.reference_stats["std_transaction_amount"] = max(
                        df["Debit"].std(), 
                        df["Credit"].std()
                    )
            
            # Grouper par date pour analyser la distribution quotidienne
            if "EcritureDate" in df.columns:
                df["Date"] = pd.to_datetime(df["EcritureDate"], errors="coerce")
                daily_counts = df.groupby(df["Date"].dt.date).size()
                
                if len(daily_counts) > 0:
                    self.reference_stats["average_transactions_per_day"] = daily_counts.mean()
            
            # Si le déséquilibre global est presque nul, mettre à jour le seuil
            if debit_sum > 0 and credit_sum > 0:
                imbalance_ratio = abs(debit_sum - credit_sum) / max(debit_sum, credit_sum)
                if imbalance_ratio < 0.001:  # Très faible déséquilibre dans les données d'entraînement
                    self.rules["balance_threshold"] = min(0.005, self.rules["balance_threshold"])
            
            # Sauvegarder le modèle mis à jour
            await self.save_model()
            
            logger.info("Modèle de détection d'anomalies entraîné avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle: {str(e)}")
            return False
    
    async def detect_anomalies(self, fec_entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """
        Détecte les anomalies dans les données FEC.
        
        Args:
            fec_entries: Liste des entrées FEC à analyser
        
        Returns:
            Liste des anomalies détectées
        """
        # Charger le modèle si ce n'est pas déjà fait
        if not self.model_loaded:
            await self.load_model()
        
        anomalies = []
        
        try:
            # Convertir en DataFrame pour faciliter l'analyse
            df = pd.DataFrame(fec_entries)
            
            # 1. Vérifier l'équilibre global débit/crédit
            balance_anomalies = await self._check_balance(df)
            anomalies.extend(balance_anomalies)
            
            # 2. Rechercher des entrées en double
            duplicate_anomalies = await self._check_duplicates(df)
            anomalies.extend(duplicate_anomalies)
            
            # 3. Détecter les montants aberrants
            outlier_anomalies = await self._check_amount_outliers(df)
            anomalies.extend(outlier_anomalies)
            
            # 4. Vérifier les activités suspectes (weekend, nuit, etc.)
            suspicious_anomalies = await self._check_suspicious_patterns(df)
            anomalies.extend(suspicious_anomalies)
            
            # 5. Vérifier les incohérences de dates
            date_anomalies = await self._check_date_inconsistencies(df)
            anomalies.extend(date_anomalies)
            
            # 6. Vérifier les patterns suspects dans les descriptions
            pattern_anomalies = await self._check_text_patterns(df)
            anomalies.extend(pattern_anomalies)
            
            logger.info(f"Détection d'anomalies terminée: {len(anomalies)} anomalies trouvées")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection des anomalies: {str(e)}")
            # En cas d'erreur, retourner un set minimal d'anomalies basé sur des vérifications simples
            return self._fallback_detection(fec_entries)
    
    async def _check_balance(self, df: pd.DataFrame) -> List[Anomaly]:
        """Vérifie l'équilibre entre les débits et crédits"""
        anomalies = []
        
        try:
            if "Debit" not in df.columns or "Credit" not in df.columns:
                # Créer une anomalie pour signaler des données manquantes
                anomalies.append(Anomaly(
                    type=AnomalyType.MISSING_DATA,
                    description="Colonnes Debit ou Credit manquantes",
                    confidence_score=1.0
                ))
                return anomalies
            
            # Calculer les totaux
            debit_sum = df["Debit"].sum()
            credit_sum = df["Credit"].sum()
            
            # Si le total des débits ou crédits est nul, c'est suspect
            if debit_sum == 0 or credit_sum == 0:
                anomalies.append(Anomaly(
                    type=AnomalyType.BALANCE_MISMATCH,
                    description=f"{'Débit' if debit_sum == 0 else 'Crédit'} total nul",
                    confidence_score=0.95,
                    related_data={"debit_sum": debit_sum, "credit_sum": credit_sum}
                ))
                return anomalies
            
            # Calculer l'écart relatif
            balance_diff = abs(debit_sum - credit_sum)
            relative_diff = balance_diff / max(debit_sum, credit_sum)
            
            # Si l'écart dépasse le seuil, créer une anomalie
            if relative_diff > self.rules["balance_threshold"]:
                confidence = min(1.0, relative_diff * 10)  # Plus l'écart est grand, plus la confiance est élevée
                
                anomalies.append(Anomaly(
                    type=AnomalyType.BALANCE_MISMATCH,
                    description=f"Déséquilibre entre débits et crédits: {balance_diff:.2f} ({relative_diff:.2%})",
                    confidence_score=confidence,
                    related_data={
                        "debit_sum": debit_sum,
                        "credit_sum": credit_sum,
                        "difference": balance_diff,
                        "relative_difference": relative_diff
                    }
                ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'équilibre: {str(e)}")
            return anomalies
    
    async def _check_duplicates(self, df: pd.DataFrame) -> List[Anomaly]:
        """Détecte les entrées en double"""
        anomalies = []
        
        try:
            # Vérifier que le DataFrame n'est pas vide
            if df.empty:
                return anomalies
            
            # Colonnes à vérifier pour les doublons (comptes, dates, montants)
            dup_cols = []
            essential_cols = ["CompteNum", "EcritureDate", "Debit", "Credit", "EcritureLib"]
            
            for col in essential_cols:
                if col in df.columns:
                    dup_cols.append(col)
            
            if len(dup_cols) < 3:  # Pas assez de colonnes pour détecter des doublons fiables
                return anomalies
            
            # Rechercher les doublons strictes
            duplicates = df.duplicated(subset=dup_cols, keep='first')
            duplicate_indices = df[duplicates].index.tolist()
            
            if duplicate_indices:
                # Grouper les doublons pour créer des anomalies distinctes
                duplicate_groups = {}
                
                for idx in duplicate_indices:
                    row = df.loc[idx]
                    duplicate_key = tuple(row[col] for col in dup_cols)
                    
                    if duplicate_key not in duplicate_groups:
                        duplicate_groups[duplicate_key] = []
                    
                    duplicate_groups[duplicate_key].append(idx)
                
                # Créer une anomalie par groupe de doublons
                for dup_key, indices in duplicate_groups.items():
                    description = f"Entrées en double détectées: {len(indices) + 1} occurrences"
                    
                    # Ajouter la première occurrence (qui n'est pas dans duplicate_indices)
                    original_idx = df[df.apply(lambda x: tuple(x[col] for col in dup_cols) == dup_key, axis=1)].index[0]
                    all_indices = [original_idx] + indices
                    
                    anomalies.append(Anomaly(
                        type=AnomalyType.DUPLICATE_ENTRY,
                        description=description,
                        confidence_score=0.95,
                        line_numbers=all_indices,
                        related_data={
                            "duplicate_columns": dup_cols,
                            "duplicate_values": {col: dup_key[i] for i, col in enumerate(dup_cols)}
                        }
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des doublons: {str(e)}")
            return anomalies
    
    async def _check_amount_outliers(self, df: pd.DataFrame) -> List[Anomaly]:
        """Détecte les montants aberrants"""
        anomalies = []
        
        try:
            amount_cols = []
            if "Debit" in df.columns:
                amount_cols.append("Debit")
            if "Credit" in df.columns:
                amount_cols.append("Credit")
            
            if not amount_cols:
                return anomalies
            
            for col in amount_cols:
                # Calculer la moyenne et l'écart-type
                mean = df[col].mean()
                std = df[col].std()
                
                if std == 0:  # Éviter division par zéro
                    continue
                
                # Calculer le Z-score pour chaque valeur
                z_scores = np.abs((df[col] - mean) / std)
                
                # Identifier les outliers
                threshold = self.rules["amount_outlier_zscore"]
                outlier_indices = df[z_scores > threshold].index.tolist()
                
                # Limiter le nombre d'anomalies pour éviter d'en rapporter trop
                max_outliers = 10
                if len(outlier_indices) > max_outliers:
                    # Trier par Z-score décroissant et garder les plus extrêmes
                    outlier_scores = [(idx, z_scores[idx]) for idx in outlier_indices]
                    outlier_scores.sort(key=lambda x: x[1], reverse=True)
                    outlier_indices = [idx for idx, _ in outlier_scores[:max_outliers]]
                
                for idx in outlier_indices:
                    amount = df.loc[idx, col]
                    z_score = z_scores[idx]
                    confidence = min(0.95, z_score / (threshold * 2))  # Normaliser la confiance
                    
                    anomalies.append(Anomaly(
                        type=AnomalyType.SUSPICIOUS_PATTERN,
                        description=f"Montant {col} aberrant: {amount:.2f}",
                        confidence_score=confidence,
                        line_numbers=[idx],
                        related_data={
                            "amount": amount,
                            "z_score": z_score,
                            "mean": mean,
                            "std": std,
                            "account": df.loc[idx, "CompteNum"] if "CompteNum" in df.columns else None,
                            "description": df.loc[idx, "EcritureLib"] if "EcritureLib" in df.columns else None
                        }
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des montants aberrants: {str(e)}")
            return anomalies
    
    async def _check_suspicious_patterns(self, df: pd.DataFrame) -> List[Anomaly]:
        """Détecte les patterns d'activité suspects (weekend, nuit, etc.)"""
        anomalies = []
        
        try:
            if "EcritureDate" not in df.columns:
                return anomalies
            
            # Convertir les dates
            df["Date"] = pd.to_datetime(df["EcritureDate"], errors="coerce")
            
            # Entrées avec dates invalides
            invalid_dates = df["Date"].isna()
            if invalid_dates.any():
                invalid_indices = df[invalid_dates].index.tolist()
                
                anomalies.append(Anomaly(
                    type=AnomalyType.DATE_INCONSISTENCY,
                    description=f"Dates d'écriture invalides ({len(invalid_indices)} entrées)",
                    confidence_score=0.9,
                    line_numbers=invalid_indices[:10]  # Limiter à 10 exemples
                ))
            
            # Détecter les activités du weekend
            weekend_mask = df["Date"].dt.dayofweek.isin([5, 6])  # 5=Samedi, 6=Dimanche
            if weekend_mask.any():
                weekend_indices = df[weekend_mask].index.tolist()
                
                # Si plus de 5% des entrées sont le weekend, c'est peut-être normal pour cette entreprise
                weekend_pct = len(weekend_indices) / len(df)
                if weekend_pct < 0.05:
                    anomalies.append(Anomaly(
                        type=AnomalyType.SUSPICIOUS_PATTERN,
                        description=f"Activité comptable le weekend ({len(weekend_indices)} entrées)",
                        confidence_score=self.rules["weekend_activity_score"],
                        line_numbers=weekend_indices[:10]  # Limiter à 10 exemples
                    ))
            
            # Détecter les sauts dans la numérotation des écritures
            if "EcritureNum" in df.columns:
                try:
                    df["EcritureNum_int"] = pd.to_numeric(df["EcritureNum"], errors="coerce")
                    df_sorted = df.sort_values("EcritureNum_int")
                    df_sorted.reset_index(inplace=True)
                    
                    # Calculer les différences entre numéros consécutifs
                    df_sorted["num_diff"] = df_sorted["EcritureNum_int"].diff()
                    
                    # Identifier les sauts importants (plus de 2)
                    gaps = df_sorted[df_sorted["num_diff"] > 2]
                    
                    if len(gaps) > 0:
                        # Limiter le nombre de sauts à rapporter
                        max_gaps = 5
                        if len(gaps) > max_gaps:
                            gaps = gaps.nlargest(max_gaps, "num_diff")
                        
                        gap_details = []
                        for _, row in gaps.iterrows():
                            gap_details.append({
                                "before": row["EcritureNum"],
                                "gap_size": row["num_diff"],
                                "index": row["index"]
                            })
                        
                        anomalies.append(Anomaly(
                            type=AnomalyType.SUSPICIOUS_PATTERN,
                            description=f"Sauts dans la numérotation des écritures ({len(gaps)} sauts)",
                            confidence_score=0.7,
                            related_data={"gaps": gap_details}
                        ))
                except Exception as num_error:
                    logger.warning(f"Erreur lors de l'analyse des numéros d'écriture: {str(num_error)}")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des patterns suspects: {str(e)}")
            return anomalies
    
    async def _check_date_inconsistencies(self, df: pd.DataFrame) -> List[Anomaly]:
        """Vérifie les incohérences de dates"""
        anomalies = []
        
        try:
            date_cols = []
            for col in df.columns:
                if "date" in col.lower():
                    date_cols.append(col)
            
            if len(date_cols) < 2:
                return anomalies
            
            # Convertir toutes les colonnes de dates
            for col in date_cols:
                df[f"{col}_dt"] = pd.to_datetime(df[col], errors="coerce")
            
            # Vérifier les incohérences entre dates
            for i in range(len(date_cols)):
                for j in range(i+1, len(date_cols)):
                    col1 = date_cols[i]
                    col2 = date_cols[j]
                    
                    dt_col1 = f"{col1}_dt"
                    dt_col2 = f"{col2}_dt"
                    
                    # Ignorer les dates manquantes
                    valid_mask = ~df[dt_col1].isna() & ~df[dt_col2].isna()
                    
                    if valid_mask.sum() == 0:
                        continue
                    
                    # Cas particulier: PieceDate devrait être <= EcritureDate
                    specific_check = False
                    expected_order = None
                    
                    if "PieceDate" in [col1, col2] and "EcritureDate" in [col1, col2]:
                        specific_check = True
                        if col1 == "PieceDate":
                            expected_order = df[dt_col1] <= df[dt_col2]
                        else:
                            expected_order = df[dt_col2] <= df[dt_col1]
                    
                    if specific_check and expected_order is not None:
                        invalid_order = ~expected_order & valid_mask
                        
                        if invalid_order.any():
                            invalid_indices = df[invalid_order].index.tolist()
                            
                            anomalies.append(Anomaly(
                                type=AnomalyType.DATE_INCONSISTENCY,
                                description=f"Incohérence entre dates: {col1} devrait être <= {col2} ({len(invalid_indices)} entrées)",
                                confidence_score=0.85,
                                line_numbers=invalid_indices[:10]
                            ))
                    
                    # Vérification générale: grands écarts entre dates liées
                    else:
                        df["date_diff_days"] = abs((df[dt_col1] - df[dt_col2]).dt.days)
                        large_diff = (df["date_diff_days"] > 60) & valid_mask
                        
                        if large_diff.any():
                            large_diff_indices = df[large_diff].index.tolist()
                            
                            anomalies.append(Anomaly(
                                type=AnomalyType.DATE_INCONSISTENCY,
                                description=f"Grand écart entre dates {col1} et {col2} (> 60 jours, {len(large_diff_indices)} entrées)",
                                confidence_score=0.6,
                                line_numbers=large_diff_indices[:10]
                            ))
            
            # Vérifier les dates futures
            if "EcritureDate_dt" in df.columns:
                today = pd.Timestamp.now().normalize()
                future_dates = df["EcritureDate_dt"] > today
                
                if future_dates.any():
                    future_indices = df[future_dates].index.tolist()
                    
                    anomalies.append(Anomaly(
                        type=AnomalyType.DATE_INCONSISTENCY,
                        description=f"Dates d'écriture futures ({len(future_indices)} entrées)",
                        confidence_score=0.9,
                        line_numbers=future_indices[:10]
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des incohérences de dates: {str(e)}")
            return anomalies
    
    async def _check_text_patterns(self, df: pd.DataFrame) -> List[Anomaly]:
        """Vérifie les patterns suspects dans les champs textuels"""
        anomalies = []
        
        try:
            if "EcritureLib" not in df.columns:
                return anomalies
            
            suspicious_patterns = self.rules.get("suspicious_patterns", [])
            
            for pattern_info in suspicious_patterns:
                pattern = pattern_info["pattern"]
                confidence = pattern_info.get("confidence", 0.6)
                
                # Rechercher le pattern en ignorant la casse
                if isinstance(pattern, str):
                    pattern_mask = df["EcritureLib"].str.contains(pattern, case=False, na=False)
                    
                    if pattern_mask.any():
                        pattern_indices = df[pattern_mask].index.tolist()
                        
                        anomalies.append(Anomaly(
                            type=AnomalyType.SUSPICIOUS_PATTERN,
                            description=f"Libellé suspect contenant '{pattern}' ({len(pattern_indices)} entrées)",
                            confidence_score=confidence,
                            line_numbers=pattern_indices[:10]
                        ))
            
            # Rechercher les caractères spéciaux excessifs
            special_char_mask = df["EcritureLib"].str.contains(r'[!@#$%^&*(){}\[\]|\\<>?]', regex=True, na=False)
            
            if special_char_mask.any():
                special_char_indices = df[special_char_mask].index.tolist()
                
                anomalies.append(Anomaly(
                    type=AnomalyType.SUSPICIOUS_PATTERN,
                    description=f"Libellé avec caractères spéciaux ({len(special_char_indices)} entrées)",
                    confidence_score=0.5,
                    line_numbers=special_char_indices[:10]
                ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des patterns textuels: {str(e)}")
            return anomalies
    
    def _fallback_detection(self, fec_entries: List[Dict[str, Any]]) -> List[Anomaly]:
        """Détection d'anomalies de secours en cas d'erreur"""
        anomalies = []
        
        try:
            # Vérification basique de l'équilibre total débit/crédit
            total_debit = sum(entry.get("Debit", 0) for entry in fec_entries)
            total_credit = sum(entry.get("Credit", 0) for entry in fec_entries)
            
            if total_debit != total_credit:
                diff = abs(total_debit - total_credit)
                relative_diff = diff / max(total_debit, total_credit) if max(total_debit, total_credit) > 0 else 1.0
                
                if relative_diff > 0.01:  # Écart de plus de 1%
                    anomalies.append(Anomaly(
                        type=AnomalyType.BALANCE_MISMATCH,
                        description=f"Déséquilibre débit/crédit: {diff:.2f} ({relative_diff:.2%})",
                        confidence_score=0.9,
                        related_data={"total_debit": total_debit, "total_credit": total_credit}
                    ))
            
            # Vérification basique des entrées manquant des informations essentielles
            missing_info_count = 0
            missing_info_lines = []
            
            for i, entry in enumerate(fec_entries):
                essential_fields = ["CompteNum", "EcritureDate", "EcritureLib"]
                missing_fields = [field for field in essential_fields if not entry.get(field)]
                
                if missing_fields:
                    missing_info_count += 1
                    missing_info_lines.append(i)
                    
                    if len(missing_info_lines) <= 10:  # Limiter le nombre d'exemples
                        anomalies.append(Anomaly(
                            type=AnomalyType.MISSING_DATA,
                            description=f"Données manquantes: {', '.join(missing_fields)}",
                            confidence_score=0.8,
                            line_numbers=[i],
                            related_data={"missing_fields": missing_fields}
                        ))
            
            # Si trop d'entrées ont des données manquantes, créer une anomalie globale
            if missing_info_count > 10:
                anomalies.append(Anomaly(
                    type=AnomalyType.MISSING_DATA,
                    description=f"Données essentielles manquantes dans {missing_info_count} entrées",
                    confidence_score=0.9,
                    line_numbers=missing_info_lines[:20]  # Limiter les exemples
                ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection de secours: {str(e)}")
            # Retourner au moins une anomalie pour signaler un problème
            return [Anomaly(
                type=AnomalyType.CALCULATION_ERROR,
                description="Erreur lors de l'analyse du fichier",
                confidence_score=1.0,
                related_data={"error": str(e)}
            )]
    
    async def generate_training_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Génère des données FEC pour l'entraînement en utilisant le générateur FEC.
        
        Args:
            count: Nombre de jeux de données à générer
        
        Returns:
            Liste de jeux de données FEC
        """
        if not self.fec_generator:
            logger.error("Pas de générateur FEC disponible pour la génération de données d'entraînement")
            return []
        
        try:
            datasets = []
            
            for i in range(count):
                dataset = await self.fec_generator.generate_fec_data(
                    num_entries=random.randint(100, 500),
                    with_anomalies=False  # Données propres pour l'entraînement
                )
                datasets.append(dataset)
            
            logger.info(f"{count} jeux de données FEC générés pour l'entraînement")
            return datasets
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de données d'entraînement: {str(e)}")
            return []


@lru_cache()
def get_anomaly_detector() -> AnomalyDetector:
    """Singleton pour récupérer le détecteur d'anomalies"""
    return AnomalyDetector(get_fec_generator())