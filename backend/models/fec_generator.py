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
    Générateur de fichiers FEC pour les tests et l'entraînement du modèle
    """
    
    def __init__(self, 
                 start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None,
                 anomaly_rate: float = 0.05):
        """
        Initialise le générateur de FEC
        
        Args:
            start_date: Date de début des écritures (par défaut: début de l'année)
            end_date: Date de fin des écritures (par défaut: aujourd'hui)
            anomaly_rate: Taux d'anomalies à introduire (0.0 à 1.0)
        """
        self.start_date = start_date or datetime(datetime.now().year, 1, 1)
        self.end_date = end_date or datetime.now()
        self.anomaly_rate = min(1.0, max(0.0, anomaly_rate))
        
        # Configuration de base
        self.company_name = "ENTREPRISE EXAMPLE SAS"
        self.siret = f"{random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(10000, 99999)}"
        
        # Journaux comptables
        self.journals = {
            "ACH": "Journal des achats",
            "VTE": "Journal des ventes",
            "BNQ": "Journal de banque",
            "OD": "Opérations diverses",
            "CAI": "Journal de caisse",
            "NDF": "Notes de frais"
        }
        
        # Plan comptable simplifié
        self.accounts = {
            # Classe 1 - Comptes de capitaux
            "101000": "Capital social",
            "106100": "Réserve légale",
            "120000": "Résultat de l'exercice",
            "164000": "Emprunts auprès des établissements de crédit",
            
            # Classe 2 - Comptes d'immobilisations
            "205000": "Logiciels et licences",
            "213500": "Installations générales, aménagements",
            "215000": "Matériel de bureau et informatique",
            "218000": "Autres immobilisations corporelles",
            "280500": "Amortissements logiciels et licences",
            "281350": "Amortissements installations",
            "281500": "Amortissements matériel de bureau et informatique",
            
            # Classe 4 - Comptes de tiers
            "401000": "Fournisseurs",
            "404000": "Fournisseurs d'immobilisations",
            "411000": "Clients",
            "425000": "Personnel - avances et acomptes",
            "431000": "Sécurité sociale",
            "444000": "Etat - impôts sur les bénéfices",
            "445510": "TVA à décaisser",
            "445620": "TVA déductible sur immobilisations",
            "445660": "TVA déductible sur autres biens et services",
            "445710": "TVA collectée",
            
            # Classe 5 - Comptes financiers
            "512000": "Banque",
            "530000": "Caisse",
            
            # Classe 6 - Comptes de charges
            "601000": "Achats de matières premières",
            "602100": "Achats de fournitures non stockables",
            "604000": "Achats de prestations de services",
            "606100": "Fournitures non stockables (eau, énergie)",
            "606300": "Fournitures d'entretien et de petit équipement",
            "606400": "Fournitures administratives",
            "611000": "Sous-traitance générale",
            "613200": "Locations immobilières",
            "615000": "Entretien et réparations",
            "616000": "Primes d'assurance",
            "622600": "Honoraires",
            "623000": "Publicité, publications, relations publiques",
            "625100": "Voyages et déplacements",
            "626000": "Frais postaux et télécommunications",
            "627000": "Services bancaires",
            "631000": "Impôts, taxes et versements assimilés sur rémunérations",
            "641000": "Rémunération du personnel",
            "645000": "Charges de sécurité sociale et de prévoyance",
            "651000": "Redevances pour concessions, licences...",
            "661000": "Charges d'intérêts",
            "681120": "Dotations aux amortissements immobilisations corporelles",
            
            # Classe 7 - Comptes de produits
            "701000": "Ventes de produits finis",
            "706000": "Prestations de services",
            "707000": "Ventes de marchandises",
            "708500": "Ports et frais accessoires facturés",
            "764000": "Revenus des valeurs mobilières de placement",
            "775000": "Produits des cessions d'éléments d'actif",
        }
        
        # Fournisseurs fictifs
        self.suppliers = [
            "Fournitures Express SARL",
            "Matériel Pro SA",
            "Bureau Concept",
            "InfoTech Solutions",
            "ServicePlus Maintenance",
            "Imprimerie Rapide",
            "Transport Express",
            "Nettoyage Services",
            "Sécurité Entreprise",
            "Communication & Marketing"
        ]
        
        # Clients fictifs
        self.clients = [
            "Client Distribution SA",
            "Entreprise Martin",
            "Groupe Leroy",
            "Société Dupont",
            "Industries Lambert",
            "Commerce Central",
            "Services Généraux",
            "International Business",
            "Agence Créative",
            "Solutions Professionnelles"
        ]
        
        # Descriptions d'écritures par type de journal
        self.descriptions = {
            "ACH": [
                "Achat fournitures bureau", 
                "Achat matériel informatique", 
                "Achat consommables", 
                "Services maintenance", 
                "Prestation conseil"
            ],
            "VTE": [
                "Facture vente produit", 
                "Prestation service client", 
                "Vente marchandises", 
                "Service maintenance", 
                "Formation client"
            ],
            "BNQ": [
                "Virement bancaire", 
                "Prélèvement automatique", 
                "Remise de chèque", 
                "Frais bancaires", 
                "Paiement carte"
            ],
            "OD": [
                "Dotation amortissement", 
                "Régularisation TVA", 
                "Provision charges", 
                "Extourne écriture", 
                "Ecart de règlement"
            ],
            "CAI": [
                "Remboursement frais", 
                "Achat petites fournitures", 
                "Frais de représentation", 
                "Réception client", 
                "Petite caisse"
            ],
            "NDF": [
                "Note de frais déplacement", 
                "Frais restaurant client", 
                "Frais transport", 
                "Frais hébergement", 
                "Frais divers"
            ]
        }
    
    def _generate_transaction_date(self) -> datetime:
        """Génère une date aléatoire entre start_date et end_date"""
        days_range = (self.end_date - self.start_date).days
        if days_range <= 0:
            return self.start_date
        random_days = random.randint(0, days_range)
        return self.start_date + timedelta(days=random_days)
    
    def _get_account_pairs(self, journal_code: str) -> List[Tuple[str, str]]:
        """Retourne des paires de comptes appropriées pour le journal donné"""
        if journal_code == "ACH":
            return [
                ("401000", random.choice(["601000", "602100", "604000", "606100", "606300", "606400"])),
                ("401000", random.choice(["611000", "613200", "615000", "616000", "622600"]))
            ]
        elif journal_code == "VTE":
            return [
                (random.choice(["701000", "706000", "707000"]), "411000"),
                ("411000", "707000")
            ]
        elif journal_code == "BNQ":
            return [
                ("512000", "401000"),
                ("411000", "512000"),
                ("512000", "661000"),
                ("641000", "512000")
            ]
        elif journal_code == "OD":
            return [
                ("681120", random.choice(["280500", "281350", "281500"])),
                ("445510", "445710"),
                ("401000", "512000"),
                ("411000", "701000")
            ]
        elif journal_code == "CAI":
            return [
                ("530000", random.choice(["625100", "623000", "606400"])),
                ("530000", "512000")
            ]
        elif journal_code == "NDF":
            return [
                ("625100", "512000"),
                ("623000", "425000")
            ]
        
        # Défaut
        return [("401000", "602100"), ("411000", "707000")]
    
    def _generate_amount(self, journal_code: str) -> float:
        """Génère un montant approprié selon le type de journal"""
        if journal_code == "ACH":
            return round(random.uniform(50, 2000), 2)
        elif journal_code == "VTE":
            return round(random.uniform(100, 5000), 2)
        elif journal_code == "BNQ":
            return round(random.uniform(100, 10000), 2)
        elif journal_code == "OD":
            return round(random.uniform(200, 20000), 2)
        elif journal_code == "CAI":
            return round(random.uniform(10, 500), 2)
        elif journal_code == "NDF":
            return round(random.uniform(20, 300), 2)
        
        # Défaut
        return round(random.uniform(50, 1000), 2)
    
    def _inject_anomaly(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Injecte une anomalie dans l'entrée comptable"""
        anomaly_type = random.choice([
            "missing_data",
            "incorrect_format",
            "duplicate_entry",
            "balance_mismatch",
            "date_inconsistency"
        ])
        
        # Clone l'entrée pour ne pas modifier l'original
        anomaly_entry = entry.copy()
        
        if anomaly_type == "missing_data":
            # Supprime un champ important
            field_to_remove = random.choice(["compte_num", "compte_lib", "ecriture_lib"])
            anomaly_entry[field_to_remove] = ""
            anomaly_entry["_anomaly_type"] = "missing_data"
            anomaly_entry["_anomaly_description"] = f"Champ {field_to_remove} manquant"
            
        elif anomaly_type == "incorrect_format":
            # Format incorrect dans un champ
            anomaly_entry["compte_num"] = f"X{anomaly_entry['compte_num'][1:]}"
            anomaly_entry["_anomaly_type"] = "incorrect_format"
            anomaly_entry["_anomaly_description"] = "Format de compte incorrect"
            
        elif anomaly_type == "duplicate_entry":
            # Pas de modification, sera dupliqué lors de la génération
            anomaly_entry["_anomaly_type"] = "duplicate_entry"
            anomaly_entry["_anomaly_description"] = "Entrée dupliquée"
            
        elif anomaly_type == "balance_mismatch":
            # Déséquilibre entre débit et crédit
            if anomaly_entry["debit_montant"] > 0:
                anomaly_entry["debit_montant"] += random.uniform(0.01, 10)
            else:
                anomaly_entry["credit_montant"] += random.uniform(0.01, 10)
                
            anomaly_entry["_anomaly_type"] = "balance_mismatch"
            anomaly_entry["_anomaly_description"] = "Déséquilibre débit/crédit"
            
        elif anomaly_type == "date_inconsistency":
            # Incohérence de dates
            piece_date = datetime.strptime(anomaly_entry["piece_date"], "%Y-%m-%d")
            modified_date = piece_date - timedelta(days=random.randint(30, 60))
            anomaly_entry["piece_date"] = modified_date.strftime("%Y-%m-%d")
            
            anomaly_entry["_anomaly_type"] = "date_inconsistency"
            anomaly_entry["_anomaly_description"] = "Incohérence de date pièce/écriture"
        
        return anomaly_entry
    
    def generate_entries(self, count: int = 1000) -> List[Dict[str, Any]]:
        """
        Génère un ensemble d'écritures comptables FEC
        
        Args:
            count: Nombre d'écritures à générer
            
        Returns:
            Liste de dictionnaires représentant les écritures comptables
        """
        entries = []
        entry_count = 0
        anomalies_count = 0
        
        # Nombre d'anomalies à créer
        total_anomalies = int(count * self.anomaly_rate)
        
        while entry_count < count:
            # Choisir un journal au hasard
            journal_code = random.choice(list(self.journals.keys()))
            journal_lib = self.journals[journal_code]
            
            # Générer une date aléatoire
            transaction_date = self._generate_transaction_date()
            
            # Choisir une description appropriée pour ce journal
            ecriture_lib = random.choice(self.descriptions[journal_code])
            
            # Générer une référence de pièce comptable
            piece_ref = f"{journal_code}{transaction_date.strftime('%Y%m')}-{random.randint(1000, 9999)}"
            
            # Obtenir des comptes appropriés pour ce journal
            debit_account, credit_account = random.choice(self._get_account_pairs(journal_code))
            
            # Générer un montant approprié
            amount = self._generate_amount(journal_code)
            
            # Créer deux écritures (débit et crédit)
            for i, (compte_num, is_debit) in enumerate([
                (debit_account, True),
                (credit_account, False)
            ]):
                compte_lib = self.accounts.get(compte_num, "Compte inconnu")
                
                # Informations sur le tiers (client/fournisseur)
                comp_aux_num = ""
                comp_aux_lib = ""
                
                if compte_num == "401000":  # Fournisseur
                    comp_aux_num = f"F{random.randint(10000, 99999)}"
                    comp_aux_lib = random.choice(self.suppliers)
                elif compte_num == "411000":  # Client
                    comp_aux_num = f"C{random.randint(10000, 99999)}"
                    comp_aux_lib = random.choice(self.clients)
                
                entry = {
                    "journal_code": journal_code,
                    "journal_lib": journal_lib,
                    "ecr_num": f"ECR{entry_count+1:06d}",
                    "ecr_date": transaction_date.strftime("%Y-%m-%d"),
                    "compte_num": compte_num,
                    "compte_lib": compte_lib,
                    "comp_aux_num": comp_aux_num,
                    "comp_aux_lib": comp_aux_lib,
                    "piece_ref": piece_ref,
                    "piece_date": transaction_date.strftime("%Y-%m-%d"),
                    "ecriture_lib": ecriture_lib,
                    "debit_montant": amount if is_debit else 0,
                    "credit_montant": 0 if is_debit else amount,
                    "ecriture_date": transaction_date.strftime("%Y-%m-%d"),
                    "validation_date": (transaction_date + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d") if random.random() > 0.2 else None
                }
                
                # Déterminer si on doit injecter une anomalie
                if anomalies_count < total_anomalies and random.random() < (self.anomaly_rate * 2):
                    entry = self._inject_anomaly(entry)
                    anomalies_count += 1
                    
                    # Pour les duplications, ajouter l'entrée deux fois
                    if entry.get("_anomaly_type") == "duplicate_entry":
                        entries.append(entry)
                        entry_count += 1
                
                entries.append(entry)
                entry_count += 1
                
                # Vérifier si on a atteint le nombre total demandé
                if entry_count >= count:
                    break
        
        logger.info(f"Généré {entry_count} écritures comptables avec {anomalies_count} anomalies")
        return entries
    
    def save_to_csv(self, entries: List[Dict[str, Any]], output_path: str) -> str:
        """
        Enregistre les écritures générées dans un fichier CSV au format FEC
        
        Args:
            entries: Liste des écritures à enregistrer
            output_path: Chemin du fichier de sortie
            
        Returns:
            Chemin du fichier créé
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Déterminer les champs à partir des clés du premier élément
            fieldnames = [k for k in entries[0].keys() if not k.startswith('_')]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            
            for entry in entries:
                # Filtrer pour ne pas inclure les métadonnées d'anomalies
                filtered_entry = {k: v for k, v in entry.items() if not k.startswith('_')}
                writer.writerow(filtered_entry)
        
        logger.info(f"Fichier FEC enregistré: {output_path}")
        return output_path


# Exemple d'utilisation
if __name__ == "__main__":
    # Configurer le logger
    logging.basicConfig(level=logging.INFO)
    
    # Créer le générateur
    generator = FECGenerator(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        anomaly_rate=0.05  # 5% d'anomalies
    )
    
    # Générer des écritures
    entries = generator.generate_entries(count=2000)
    
    # Enregistrer au format CSV
    output_file = "data/generated_fec_sample.csv"
    generator.save_to_csv(entries, output_file)


@lru_cache()
def get_fec_generator() -> FECGenerator:
    """Singleton pour récupérer le générateur FEC"""
    return FECGenerator()