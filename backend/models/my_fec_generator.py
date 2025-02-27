"""
Module pour générer des données FEC factices.
"""
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import json
import os
import pandas as pd
from faker import Faker

from backend.models.schemas import AnomalyType
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MyFECGenerator:
    """Générateur de données FEC (Fichier des Ecritures Comptables)"""
    
    def __init__(self, 
                company_name: str = "EMPRESA_TEST", 
                start_date: str = "2023-01-01",
                end_date: str = "2023-12-31",
                transaction_count: int = 1000,
                anomaly_rate: float = 0.05):
        """
        Initialise le générateur de données FEC
        
        Args:
            company_name: Nom de l'entreprise
            start_date: Date de début pour les écritures (format YYYY-MM-DD)
            end_date: Date de fin pour les écritures (format YYYY-MM-DD)
            transaction_count: Nombre d'écritures à générer
            anomaly_rate: Taux d'anomalies à introduire (0.0 - 1.0)
        """
        self.faker = Faker('fr_FR')
        self.company_name = company_name
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.transaction_count = transaction_count
        self.anomaly_rate = max(0.0, min(1.0, anomaly_rate))  # Limiter entre 0 et 1
        
        # Charger les données de référence
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Charge les données de référence pour la génération"""
        self.accounts = {
            # Classe 1 - Comptes de capitaux
            "101000": "Capital",
            "106100": "Réserve légale",
            "120000": "Résultat de l'exercice",
            "164000": "Emprunts auprès des établissements de crédit",
            
            # Classe 2 - Comptes d'immobilisations
            "205000": "Logiciels",
            "213500": "Installations générales",
            "218300": "Matériel de bureau et informatique",
            "281830": "Amortissements du matériel de bureau",
            
            # Classe 4 - Comptes de tiers
            "401000": "Fournisseurs",
            "411000": "Clients",
            "421000": "Personnel - rémunérations dues",
            "431000": "Sécurité sociale",
            "445660": "TVA déductible",
            "445710": "TVA collectée",
            "455000": "Associés - comptes courants",
            
            # Classe 5 - Comptes financiers
            "512000": "Banque",
            "530000": "Caisse",
            
            # Classe 6 - Comptes de charges
            "601000": "Achats de matières premières",
            "606300": "Fournitures d'entretien et petit équipement",
            "606400": "Fournitures administratives",
            "606800": "Autres matières et fournitures",
            "613200": "Locations immobilières",
            "615000": "Entretien et réparations",
            "616000": "Primes d'assurance",
            "622600": "Honoraires",
            "623000": "Publicité, publications, relations publiques",
            "625100": "Voyages et déplacements",
            "626000": "Frais postaux et de télécommunications",
            "627000": "Services bancaires",
            "641100": "Salaires et appointements",
            "645000": "Charges de sécurité sociale",
            "681120": "Dotations aux amortissements",
            
            # Classe 7 - Comptes de produits
            "701000": "Ventes de produits finis",
            "706000": "Prestations de services",
            "708500": "Ports et frais facturés",
            "764000": "Revenus des titres de placements",
            "775000": "Produits des cessions d'éléments d'actif",
        }
        
        self.journals = {
            "AC": "Achats",
            "VE": "Ventes",
            "BQ": "Banque",
            "CA": "Caisse",
            "OD": "Opérations diverses",
            "AN": "À nouveau"
        }
        
        self.expense_descriptions = [
            "Fournitures de bureau",
            "Honoraires comptables",
            "Location bureaux",
            "Frais de déplacement",
            "Assurance professionnelle",
            "Électricité et eau",
            "Maintenance informatique",
            "Communication et marketing",
            "Formation du personnel",
            "Carburant véhicule société"
        ]
        
        self.sales_descriptions = [
            "Facture client",
            "Prestation de conseil",
            "Vente de marchandises",
            "Services professionnels",
            "Abonnement mensuel",
            "Maintenance annuelle",
            "Formation client",
            "Développement logiciel",
            "Audit qualité",
            "Étude de marché"
        ]
    
    def generate_entries(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Génère un ensemble d'écritures comptables
        
        Args:
            count: Nombre d'écritures à générer (utilise transaction_count si None)
            
        Returns:
            Liste des écritures générées
        """
        if count is None:
            count = self.transaction_count
            
        entries = []
        
        # Définir un intervalle de temps pour distribuer les écritures
        date_range = (self.end_date - self.start_date).days
        
        # Générer des écritures pour chaque jour de l'intervalle
        current_date = self.start_date
        entry_num = 1
        
        # Répartir le nombre d'écritures sur l'intervalle de temps
        entries_per_day = max(1, count // (date_range or 1))
        remaining_entries = count
        
        while current_date <= self.end_date and remaining_entries > 0:
            # Nombre d'écritures pour ce jour
            day_entries = min(entries_per_day + random.randint(-2, 2), remaining_entries)
            
            # Générer les écritures du jour
            for _ in range(day_entries):
                # Choisir aléatoirement un type d'écriture
                entry_type = random.choice(["expense", "sales", "salary", "misc"])
                
                if entry_type == "expense":
                    new_entries = self._generate_expense_entry(current_date, entry_num)
                elif entry_type == "sales":
                    new_entries = self._generate_sales_entry(current_date, entry_num)
                elif entry_type == "salary":
                    new_entries = self._generate_salary_entry(current_date, entry_num)
                else:
                    new_entries = self._generate_misc_entry(current_date, entry_num)
                
                entries.extend(new_entries)
                entry_num += 1
                remaining_entries -= 1
            
            # Passer au jour suivant
            current_date += timedelta(days=1)
        
        # Introduire des anomalies selon le taux défini
        if self.anomaly_rate > 0:
            self._introduce_anomalies(entries)
        
        logger.info(f"Généré {len(entries)} écritures au total")
        return entries
    
    def _generate_expense_entry(self, date: datetime, entry_num: int) -> List[Dict[str, Any]]:
        """Génère une écriture de dépense"""
        # Montant de la dépense
        amount = round(random.uniform(100, 5000), 2)
        tva_amount = round(amount * 0.2, 2)
        total_amount = amount + tva_amount
        
        # Libellé de la dépense
        description = random.choice(self.expense_descriptions)
        supplier = self.faker.company()
        lib = f"{description} - {supplier}"
        
        # Date de l'écriture
        entry_date = date.replace(
            hour=random.randint(8, 17),
            minute=random.randint(0, 59)
        )
        
        # Générer les lignes d'écriture
        entries = []
        
        # 1. Débit du compte de charges
        expense_account = random.choice(list(k for k in self.accounts.keys() if k.startswith("6")))
        entries.append({
            "journal_code": "AC",
            "journal_lib": self.journals["AC"],
            "ecr_num": f"AC{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": expense_account,
            "compte_lib": self.accounts.get(expense_account, ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"FC{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": amount,
            "credit_montant": 0,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 2. Débit de la TVA déductible
        entries.append({
            "journal_code": "AC",
            "journal_lib": self.journals["AC"],
            "ecr_num": f"AC{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "445660",
            "compte_lib": self.accounts.get("445660", ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"FC{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": tva_amount,
            "credit_montant": 0,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 3. Crédit du compte fournisseur
        entries.append({
            "journal_code": "AC",
            "journal_lib": self.journals["AC"],
            "ecr_num": f"AC{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "401000",
            "compte_lib": self.accounts.get("401000", ""),
            "comp_aux_num": supplier[:10],
            "comp_aux_lib": supplier,
            "piece_ref": f"FC{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": total_amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        return entries
    
    def _generate_sales_entry(self, date: datetime, entry_num: int) -> List[Dict[str, Any]]:
        """Génère une écriture de vente"""
        # Montant de la vente
        amount = round(random.uniform(500, 10000), 2)
        tva_amount = round(amount * 0.2, 2)
        total_amount = amount + tva_amount
        
        # Libellé de la vente
        description = random.choice(self.sales_descriptions)
        customer = self.faker.company()
        lib = f"{description} - {customer}"
        
        # Date de l'écriture
        entry_date = date.replace(
            hour=random.randint(8, 17),
            minute=random.randint(0, 59)
        )
        
        # Générer les lignes d'écriture
        entries = []
        
        # 1. Débit du compte client
        entries.append({
            "journal_code": "VE",
            "journal_lib": self.journals["VE"],
            "ecr_num": f"VE{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "411000",
            "compte_lib": self.accounts.get("411000", ""),
            "comp_aux_num": customer[:10],
            "comp_aux_lib": customer,
            "piece_ref": f"FV{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": total_amount,
            "credit_montant": 0,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 2. Crédit du compte de produits
        revenue_account = random.choice(list(k for k in self.accounts.keys() if k.startswith("7")))
        entries.append({
            "journal_code": "VE",
            "journal_lib": self.journals["VE"],
            "ecr_num": f"VE{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": revenue_account,
            "compte_lib": self.accounts.get(revenue_account, ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"FV{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 3. Crédit de la TVA collectée
        entries.append({
            "journal_code": "VE",
            "journal_lib": self.journals["VE"],
            "ecr_num": f"VE{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "445710",
            "compte_lib": self.accounts.get("445710", ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"FV{self.faker.random_number(digits=6)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": tva_amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        return entries
    
    def _generate_salary_entry(self, date: datetime, entry_num: int) -> List[Dict[str, Any]]:
        """Génère une écriture de paie"""
        # Montant des salaires
        net_amount = round(random.uniform(2000, 10000), 2)
        charges_amount = round(net_amount * 0.5, 2)
        total_amount = net_amount + charges_amount
        
        # Libellé de la paie
        lib = f"Salaires {date.strftime('%B %Y')}"
        
        # Date de l'écriture (fin du mois)
        entry_date = date.replace(day=28, hour=14, minute=random.randint(0, 59))
        
        # Générer les lignes d'écriture
        entries = []
        
        # 1. Débit des salaires bruts
        entries.append({
            "journal_code": "OD",
            "journal_lib": self.journals["OD"],
            "ecr_num": f"OD{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "641100",
            "compte_lib": self.accounts.get("641100", ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"PAIE{date.strftime('%m%Y')}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": total_amount,
            "credit_montant": 0,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 2. Crédit des cotisations sociales
        entries.append({
            "journal_code": "OD",
            "journal_lib": self.journals["OD"],
            "ecr_num": f"OD{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "431000",
            "compte_lib": self.accounts.get("431000", ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"PAIE{date.strftime('%m%Y')}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": charges_amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 3. Crédit du compte personnel
        entries.append({
            "journal_code": "OD",
            "journal_lib": self.journals["OD"],
            "ecr_num": f"OD{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": "421000",
            "compte_lib": self.accounts.get("421000", ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"PAIE{date.strftime('%m%Y')}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": net_amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        return entries
    
    def _generate_misc_entry(self, date: datetime, entry_num: int) -> List[Dict[str, Any]]:
        """Génère une écriture diverse"""
        # Montant
        amount = round(random.uniform(100, 2000), 2)
        
        # Type d'opération
        operation_types = ["Remboursement de frais", "Acompte fournisseur", "Régularisation", 
                          "Dotation aux amortissements", "Opération interne"]
        operation = random.choice(operation_types)
        lib = f"{operation} - {self.faker.bs()}"
        
        # Date de l'écriture
        entry_date = date.replace(
            hour=random.randint(8, 17),
            minute=random.randint(0, 59)
        )
        
        # Comptes à utiliser
        accounts = list(self.accounts.keys())
        debit_account = random.choice(accounts)
        credit_account = random.choice([a for a in accounts if a != debit_account])
        
        # Générer les lignes d'écriture
        entries = []
        
        # 1. Débit
        entries.append({
            "journal_code": "OD",
            "journal_lib": self.journals["OD"],
            "ecr_num": f"OD{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": debit_account,
            "compte_lib": self.accounts.get(debit_account, ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"OD{self.faker.random_number(digits=5)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": amount,
            "credit_montant": 0,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        # 2. Crédit
        entries.append({
            "journal_code": "OD",
            "journal_lib": self.journals["OD"],
            "ecr_num": f"OD{entry_num}",
            "ecr_date": entry_date.isoformat(),
            "compte_num": credit_account,
            "compte_lib": self.accounts.get(credit_account, ""),
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": f"OD{self.faker.random_number(digits=5)}",
            "piece_date": entry_date.isoformat(),
            "ecriture_lib": lib,
            "debit_montant": 0,
            "credit_montant": amount,
            "ecr_lettr": "",
            "date_lettr": "",
            "valid_date": "",
            "montant_devise": 0,
            "id_devise": "EUR",
        })
        
        return entries
    
    def _introduce_anomalies(self, entries: List[Dict[str, Any]]) -> None:
        """Introduit des anomalies dans les écritures générées"""
        num_anomalies = int(len(entries) * self.anomaly_rate)
        
        if num_anomalies == 0:
            return
        
        logger.info(f"Introduction de {num_anomalies} anomalies")
        
        # Types d'anomalies
        anomaly_types = [
            self._introduce_duplicate_entry,
            self._introduce_unbalanced_entry,
            self._introduce_round_amount,
            self._introduce_weekend_transaction,
            self._introduce_missing_data
        ]
        
        # Sélectionner des entrées aléatoires pour introduire des anomalies
        entries_indices = random.sample(range(len(entries)), min(num_anomalies, len(entries)))
        
        for idx in entries_indices:
            # Choisir un type d'anomalie
            anomaly_func = random.choice(anomaly_types)
            anomaly_func(entries, idx)
    
    def _introduce_duplicate_entry(self, entries: List[Dict[str, Any]], idx: int) -> None:
        """Introduit une entrée dupliquée"""
        if idx >= len(entries):
            return
            
        # Copier l'entrée
        entry = entries[idx].copy()
        
        # Légèrement modifier pour simuler une erreur de saisie
        if random.random() < 0.3:
            # Changer légèrement le montant (différence de quelques centimes)
            if entry.get('debit_montant', 0) > 0:
                entry['debit_montant'] += random.choice([-0.01, 0.01, -0.1, 0.1])
            if entry.get('credit_montant', 0) > 0:
                entry['credit_montant'] += random.choice([-0.01, 0.01, -0.1, 0.1])
        
        if random.random() < 0.3:
            # Changer légèrement la date
            if 'ecr_date' in entry:
                date_obj = datetime.fromisoformat(entry['ecr_date'])
                date_obj += timedelta(days=random.choice([-1, 1]))
                entry['ecr_date'] = date_obj.isoformat()
        
        # Ajouter la copie modifiée à la liste des entrées
        entries.append(entry)
        logger.debug(f"Anomalie ajoutée: Entrée dupliquée (original: ligne {idx+1})")
    
    def _introduce_unbalanced_entry(self, entries: List[Dict[str, Any]], idx: int) -> None:
        """Introduit un déséquilibre dans une écriture comptable"""
        if idx >= len(entries):
            return
            
        # Récupérer le numéro d'écriture
        ecr_num = entries[idx].get('ecr_num')
        if not ecr_num:
            return
            
        # Trouver toutes les entrées avec ce numéro d'écriture
        related_entries = [i for i, e in enumerate(entries) if e.get('ecr_num') == ecr_num]
        if len(related_entries) < 2:
            return
        
        # Choisir une entrée à modifier
        entry_idx = random.choice(related_entries)
        
        # Modifier le montant pour introduire un déséquilibre
        if entries[entry_idx].get('debit_montant', 0) > 0:
            entries[entry_idx]['debit_montant'] = round(entries[entry_idx]['debit_montant'] * 
                                                      random.uniform(1.05, 1.2), 2)
        elif entries[entry_idx].get('credit_montant', 0) > 0:
            entries[entry_idx]['credit_montant'] = round(entries[entry_idx]['credit_montant'] * 
                                                       random.uniform(1.05, 1.2), 2)
        
        logger.debug(f"Anomalie ajoutée: Écriture déséquilibrée (écriture: {ecr_num})")
    
    def _introduce_round_amount(self, entries: List[Dict[str, Any]], idx: int) -> None:
        """Introduit un montant suspicieusement rond"""
        if idx >= len(entries):
            return
            
        # Montants ronds suspects
        round_amounts = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
        
        # Choisir un montant rond
        amount = random.choice(round_amounts)
        
        # Modifier l'entrée
        if random.random() < 0.5 and 'debit_montant' in entries[idx]:
            entries[idx]['debit_montant'] = amount
            if 'credit_montant' in entries[idx]:
                entries[idx]['credit_montant'] = 0
        else:
            if 'credit_montant' in entries[idx]:
                entries[idx]['credit_montant'] = amount
                if 'debit_montant' in entries[idx]:
                    entries[idx]['debit_montant'] = 0
        
        # Ajouter une mention dans le libellé
        mention = random.choice(["Paiement", "Versement", "Règlement", "Avance", "Acompte"])
        entries[idx]['ecriture_lib'] = f"{mention} - {amount} EUR"
        
        logger.debug(f"Anomalie ajoutée: Montant rond suspect ({amount} EUR) à la ligne {idx+1}")
    
    def _introduce_weekend_transaction(self, entries: List[Dict[str, Any]], idx: int) -> None:
        """Introduit une transaction effectuée pendant le weekend"""
        if idx >= len(entries):
            return
            
        # Vérifier que l'entrée a une date
        if 'ecr_date' not in entries[idx]:
            return
            
        # Convertir la chaîne de date en objet datetime
        try:
            date_obj = datetime.fromisoformat(entries[idx]['ecr_date'])
        except ValueError:
            return
        
        # Trouver le prochain samedi ou dimanche
        days_to_add = (5 - date_obj.weekday()) % 7  # Distance jusqu'à samedi
        if days_to_add == 0:  # C'est déjà un samedi
            days_to_add = 0
        elif random.random() < 0.5:  # 50% de chance pour un dimanche
            days_to_add += 1
        
        # Modifier la date pour un weekend
        new_date = date_obj + timedelta(days=days_to_add)
        
        # Définir une heure non conventionnelle
        new_date = new_date.replace(
            hour=random.choice([1, 2, 3, 4, 22, 23]),
            minute=random.randint(0, 59)
        )
        
        # Mettre à jour la date de l'écriture
        entries[idx]['ecr_date'] = new_date.isoformat()
        
        logger.debug(f"Anomalie ajoutée: Transaction de weekend ({new_date.strftime('%A %H:%M')}) à la ligne {idx+1}")
    
    def _introduce_missing_data(self, entries: List[Dict[str, Any]], idx: int) -> None:
        """Introduit des données manquantes dans une entrée"""
        if idx >= len(entries):
            return
            
        # Champs potentiels à vider
        possible_fields = ['compte_num', 'compte_lib', 'ecriture_lib', 'piece_ref', 'piece_date']
        
        # Choisir aléatoirement 1 ou 2 champs à vider
        num_fields = random.randint(1, 2)
        fields_to_empty = random.sample([f for f in possible_fields if f in entries[idx]], 
                                       min(num_fields, len(possible_fields)))
        
        # Vider les champs choisis
        for field in fields_to_empty:
            entries[idx][field] = ""
        
        logger.debug(f"Anomalie ajoutée: Données manquantes ({', '.join(fields_to_empty)}) à la ligne {idx+1}")

