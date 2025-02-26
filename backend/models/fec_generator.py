import logging
import random
import os
import json
import csv
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import pandas as pd
import numpy as np

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FECGenerator:
    """
    Interface pour le générateur de fichiers FEC.
    Cette classe fait l'interface avec votre générateur existant.
    """
    
    def __init__(self):
        """Initialisation du générateur FEC"""
        self.output_dir = settings.GENERATED_FEC_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Charger les configurations et paramètres du générateur
        self._load_config()
    
    def _load_config(self):
        """Charge la configuration du générateur FEC"""
        # Vous pourriez charger ici vos paramètres spécifiques
        # Exemples de paramètres de configuration par défaut
        self.config = {
            "company_prefixes": ["SA", "SARL", "SAS", "EURL", "SCI"],
            "common_account_prefixes": ["401", "411", "512", "606", "707"],
            "journal_codes": ["ACH", "VTE", "BNQ", "OD", "CAISSE"],
            "max_entries_per_file": 10000,
            "default_balance_threshold": 0.001  # Écart maximal toléré pour un FEC équilibré
        }
    
    async def generate_fec_data(
        self, 
        num_entries: int = 1000, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        with_anomalies: bool = False,
        anomaly_rate: float = 0.05,
        company_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Génère des données FEC synthétiques.
        
        Args:
            num_entries: Nombre d'entrées à générer
            start_date: Date de début (par défaut: il y a un an)
            end_date: Date de fin (par défaut: aujourd'hui)
            with_anomalies: Si True, inclut des anomalies volontaires
            anomaly_rate: Taux d'anomalies à inclure (si with_anomalies=True)
            company_name: Nom de l'entreprise (généré aléatoirement si None)
            
        Returns:
            Liste de dictionnaires représentant les entrées FEC
        """
        # Initialiser les dates par défaut si non fournies
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()
            
        # Générer un nom d'entreprise si non fourni
        if not company_name:
            prefix = random.choice(self.config["company_prefixes"])
            company_name = f"{prefix} EXEMPLE {random.randint(1, 999)}"
        
        # Appeler votre générateur existant ici
        # Exemple d'interface avec votre générateur:
        try:
            logger.info(f"Génération de {num_entries} entrées FEC pour {company_name}")
            
            # ===== VOTRE CODE DE GÉNÉRATION EXISTANT ==================
            # Cette partie est un placeholder pour l'intégration de votre générateur FEC existant
            # Remplacez cette section par l'appel à votre générateur
            
            # Simulons un appel asynchrone à votre générateur existant
            await asyncio.sleep(0.1)  # Simule un traitement asynchrone
            fec_entries = self._generate_mock_fec_data(
                num_entries, 
                start_date, 
                end_date, 
                company_name,
                with_anomalies,
                anomaly_rate
            )
            # =========================================================
            
            logger.info(f"Génération terminée: {len(fec_entries)} entrées FEC")
            return fec_entries
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de données FEC: {str(e)}")
            # En cas d'erreur, retourner une liste vide
            return []
    
    async def save_fec_file(
        self, 
        fec_entries: List[Dict[str, Any]], 
        output_path: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Sauvegarde les données FEC générées dans un fichier.
        
        Args:
            fec_entries: Données FEC à sauvegarder
            output_path: Chemin du fichier de sortie (généré si None)
            company_name: Nom de l'entreprise (pour le nom de fichier si output_path=None)
            
        Returns:
            Tuple (succès, chemin_du_fichier)
        """
        if not fec_entries:
            return False, "Aucune donnée à sauvegarder"
            
        # Générer un chemin de sortie si non fourni
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company_str = company_name.replace(" ", "_") if company_name else "entreprise"
            output_path = os.path.join(self.output_dir, f"FEC_{company_str}_{timestamp}.csv")
        
        try:
            # Créer le dossier parent si nécessaire
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Extraire les en-têtes à partir du premier enregistrement
            fieldnames = list(fec_entries[0].keys())
            
            # Écrire le fichier CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                writer.writerows(fec_entries)
            
            logger.info(f"Fichier FEC sauvegardé: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du fichier FEC: {str(e)}")
            return False, str(e)
    
    async def generate_and_save_fec(
        self,
        num_entries: int = 1000,
        with_anomalies: bool = False,
        company_name: Optional[str] = None
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Génère et sauvegarde des données FEC en une seule opération.
        
        Args:
            num_entries: Nombre d'entrées à générer
            with_anomalies: Si True, inclut des anomalies volontaires
            company_name: Nom de l'entreprise
            
        Returns:
            Tuple (succès, chemin_du_fichier, données_générées)
        """
        # Générer les données
        fec_entries = await self.generate_fec_data(
            num_entries=num_entries,
            with_anomalies=with_anomalies,
            company_name=company_name
        )
        
        if not fec_entries:
            return False, "Échec de la génération de données", []
            
        # Sauvegarder les données
        success, output_path = await self.save_fec_file(
            fec_entries=fec_entries,
            company_name=company_name
        )
        
        return success, output_path, fec_entries
    
    def _generate_mock_fec_data(
        self, 
        num_entries: int, 
        start_date: datetime, 
        end_date: datetime, 
        company_name: str,
        with_anomalies: bool,
        anomaly_rate: float
    ) -> List[Dict[str, Any]]:
        """
        Génère des données FEC de démonstration (à remplacer par votre générateur).
        
        Note: Cette fonction est un placeholder pour démontrer l'interface.
              Elle doit être remplacée par l'appel à votre générateur existant.
        """
        entries = []
        date_range = (end_date - start_date).days
        
        # Générer des comptes
        accounts = {}
        for prefix in self.config["common_account_prefixes"]:
            for i in range(1, 6):  # 5 comptes par préfixe
                account_num = f"{prefix}{i:02d}"
                accounts[account_num] = f"Compte {account_num}"
        
        # Générer les écritures
        total_debit = 0
        total_credit = 0
        
        for i in range(1, num_entries + 1):
            # Déterminer la date de l'écriture
            random_days = random.randint(0, date_range)
            ecr_date = start_date + timedelta(days=random_days)
            
            # Sélectionner un journal
            journal_code = random.choice(self.config["journal_codes"])
            journal_lib = {
                "ACH": "Journal des achats",
                "VTE": "Journal des ventes",
                "BNQ": "Journal de banque",
                "OD": "Opérations diverses",
                "CAISSE": "Journal de caisse"
            }.get(journal_code, journal_code)
            
            # Numéro d'écriture
            ecr_num = f"{journal_code}{i:06d}"
            
            # Sélectionner un compte
            account_num = random.choice(list(accounts.keys()))
            account_lib = accounts[account_num]
            
            # Générer un montant (entre 10 et 10000)
            amount = round(random.uniform(10, 10000), 2)
            
            # Déterminer si c'est un débit ou un crédit
            is_debit = random.choice([True, False])
            debit = amount if is_debit else 0
            credit = 0 if is_debit else amount
            
            # Mettre à jour les totaux
            total_debit += debit
            total_credit += credit
            
            # Générer une description
            descriptions = [
                "Facture client",
                "Paiement fournisseur",
                "Virement bancaire",
                "Frais bancaires",
                "Loyer mensuel",
                "Salaire employé",
                "Charges sociales",
                "TVA collectée",
                "TVA déductible",
                "Achat fournitures"
            ]
            description = random.choice(descriptions)
            
            # Référence pièce
            piece_ref = f"PCE{random.randint(1000, 9999)}"
            piece_date = ecr_date - timedelta(days=random.randint(0, 10))
            
            # Créer l'entrée
            entry = {
                "JournalCode": journal_code,
                "JournalLib": journal_lib,
                "EcritureNum": ecr_num,
                "EcritureDate": ecr_date.strftime("%Y%m%d"),
                "CompteNum": account_num,
                "CompteLib": account_lib,
                "CompAuxNum": "",
                "CompAuxLib": "",
                "PieceRef": piece_ref,
                "PieceDate": piece_date.strftime("%Y%m%d"),
                "EcritureLib": description,
                "Debit": debit,
                "Credit": credit,
                "EcritureLet": "",
                "DateLet": "",
                "ValidDate": "",
                "Montantdevise": 0,
                "Idevise": ""
            }
            
            entries.append(entry)
        
        # Ajouter une entrée d'équilibrage si nécessaire
        if total_debit != total_credit and not with_anomalies:
            diff = total_debit - total_credit
            
            if diff > 0:
                # Ajouter un crédit
                entries.append({
                    "JournalCode": "OD",
                    "JournalLib": "Opérations diverses",
                    "EcritureNum": f"OD{num_entries+1:06d}",
                    "EcritureDate": end_date.strftime("%Y%m%d"),
                    "CompteNum": "471000",
                    "CompteLib": "Compte de régularisation",
                    "CompAuxNum": "",
                    "CompAuxLib": "",
                    "PieceRef": f"REG{random.randint(1000, 9999)}",
                    "PieceDate": end_date.strftime("%Y%m%d"),
                    "EcritureLib": "Écriture d'équilibrage",
                    "Debit": 0,
                    "Credit": diff,
                    "EcritureLet": "",
                    "DateLet": "",
                    "ValidDate": "",
                    "Montantdevise": 0,
                    "Idevise": ""
                })
            else:
                # Ajouter un débit
                entries.append({
                    "JournalCode": "OD",
                    "JournalLib": "Opérations diverses",
                    "EcritureNum": f"OD{num_entries+1:06d}",
                    "EcritureDate": end_date.strftime("%Y%m%d"),
                    "CompteNum": "471000",
                    "CompteLib": "Compte de régularisation",
                    "CompAuxNum": "",
                    "CompAuxLib": "",
                    "PieceRef": f"REG{random.randint(1000, 9999)}",
                    "PieceDate": end_date.strftime("%Y%m%d"),
                    "EcritureLib": "Écriture d'équilibrage",
                    "Debit": abs(diff),
                    "Credit": 0,
                    "EcritureLet": "",
                    "DateLet": "",
                    "ValidDate": "",
                    "Montantdevise": 0,
                    "Idevise": ""
                })
        
        # Introduire des anomalies si demandé
        if with_anomalies and entries:
            num_anomalies = int(num_entries * anomaly_rate)
            
            for _ in range(num_anomalies):
                anomaly_type = random.choice([
                    "missing_data",
                    "duplicate_entry",
                    "suspicious_amount",
                    "date_inconsistency"
                ])
                
                if anomaly_type == "missing_data":
                    # Sélectionner une entrée aléatoire et supprimer des données
                    idx = random.randint(0, len(entries) - 1)
                    field_to_clear = random.choice(["CompteNum", "EcritureLib", "PieceRef"])
                    entries[idx][field_to_clear] = ""
                
                elif anomaly_type == "duplicate_entry":
                    # Dupliquer une entrée existante
                    idx = random.randint(0, len(entries) - 1)
                    duplicate = entries[idx].copy()
                    entries.append(duplicate)
                
                elif anomaly_type == "suspicious_amount":
                    # Créer une entrée avec un montant anormalement élevé
                    idx = random.randint(0, len(entries) - 1)
                    entries[idx]["Debit"] = entries[idx]["Debit"] * 100 if entries[idx]["Debit"] > 0 else 0
                    entries[idx]["Credit"] = entries[idx]["Credit"] * 100 if entries[idx]["Credit"] > 0 else 0
                
                elif anomaly_type == "date_inconsistency":
                    # Créer une incohérence de date
                    idx = random.randint(0, len(entries) - 1)
                    # Date d'écriture antérieure à la date de pièce
                    ecr_date = datetime.strptime(entries[idx]["EcritureDate"], "%Y%m%d")
                    piece_date = ecr_date + timedelta(days=30)  # Pièce datée d'un mois après l'écriture
                    entries[idx]["PieceDate"] = piece_date.strftime("%Y%m%d")
        
        return entries


@lru_cache()
def get_fec_generator() -> FECGenerator:
    """Singleton pour récupérer le générateur FEC"""
    return FECGenerator()