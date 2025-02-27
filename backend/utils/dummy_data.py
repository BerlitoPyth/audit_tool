import random
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any

from backend.models.schemas import Anomaly, AnomalyType

logger = logging.getLogger(__name__)

def generate_dummy_anomaly(line_number: int = None) -> Anomaly:
    """
    Génère une anomalie fictive pour la démonstration
    
    Args:
        line_number: Numéro de ligne optionnel pour l'anomalie
        
    Returns:
        Une instance d'Anomaly
    """
    anomaly_types = list(AnomalyType)
    selected_type = random.choice(anomaly_types)
    
    # Déterminer le numéro de ligne si non fourni
    if not line_number:
        line_number = random.randint(1, 1000)
    
    descriptions = {
        AnomalyType.MISSING_DATA: "Données manquantes dans le champ obligatoire",
        AnomalyType.INCORRECT_FORMAT: "Format de données incorrect",
        AnomalyType.DUPLICATE_ENTRY: "Entrée dupliquée détectée",
        AnomalyType.SUSPICIOUS_PATTERN: "Motif de transaction suspect",
        AnomalyType.BALANCE_MISMATCH: "Déséquilibre entre débit et crédit",
        AnomalyType.DATE_INCONSISTENCY: "Incohérence dans les dates",
        AnomalyType.CALCULATION_ERROR: "Erreur de calcul détectée",
        AnomalyType.CUSTOM: "Anomalie personnalisée"
    }
    
    related_data = {}
    
    # Générer des données associées selon le type d'anomalie
    if selected_type == AnomalyType.MISSING_DATA:
        related_data = {
            "missing_fields": ["compte_num", "ecriture_lib"],
            "importance": "high"
        }
    elif selected_type == AnomalyType.DUPLICATE_ENTRY:
        related_data = {
            "duplicate_line": line_number + random.randint(1, 10),
            "similarity_score": round(random.uniform(0.85, 0.99), 2)
        }
    elif selected_type == AnomalyType.BALANCE_MISMATCH:
        amount = round(random.uniform(100, 10000), 2)
        related_data = {
            "expected_balance": amount,
            "actual_balance": round(amount * (1 + random.uniform(-0.2, 0.2)), 2),
            "difference": round(random.uniform(10, 500), 2)
        }
    
    return Anomaly(
        id=str(uuid.uuid4()),
        type=selected_type,
        description=descriptions.get(selected_type, "Anomalie détectée"),
        confidence_score=round(random.uniform(0.6, 0.99), 2),
        line_numbers=[line_number],
        related_data=related_data,
        detected_at=datetime.now()
    )

def generate_dummy_fec_entries(count: int = 100) -> List[Dict[str, Any]]:
    """
    Génère des entrées FEC fictives pour la démonstration
    
    Args:
        count: Nombre d'entrées à générer
        
    Returns:
        Une liste de dictionnaires représentant des entrées FEC
    """
    entries = []
    
    # Codes journal possibles
    journal_codes = ["ACH", "VTE", "BNQ", "OD", "EMPR", "REMB"]
    journal_libs = {
        "ACH": "Journal des achats",
        "VTE": "Journal des ventes",
        "BNQ": "Journal de banque",
        "OD": "Opérations diverses",
        "EMPR": "Emprunts",
        "REMB": "Remboursements"
    }
    
    # Comptes possibles
    accounts = [
        ("401000", "Fournisseurs"),
        ("411000", "Clients"),
        ("512000", "Banque"),
        ("606100", "Fournitures"),
        ("607000", "Marchandises"),
        ("707000", "Vente de marchandises")
    ]
    
    # Descriptions d'écritures possibles
    descriptions = [
        "Achat de fournitures",
        "Vente de marchandises",
        "Paiement fournisseur",
        "Encaissement client",
        "Virement interne",
        "Règlement loyer",
        "Achat stock",
        "Frais bancaires",
        "Salaire employé"
    ]
    
    # Année courante
    current_year = datetime.now().year
    
    for i in range(count):
        # Date aléatoire dans l'année en cours
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        ecr_date = datetime(current_year, month, day)
        
        # Journal
        journal_code = random.choice(journal_codes)
        journal_lib = journal_libs.get(journal_code, "Journal")
        
        # Compte
        account = random.choice(accounts)
        compte_num, compte_lib = account
        
        # Montants (soit débit, soit crédit)
        is_debit = random.choice([True, False])
        amount = round(random.uniform(10, 5000), 2)
        debit = amount if is_debit else 0
        credit = 0 if is_debit else amount
        
        # Pièce
        piece_ref = f"PC{current_year}{month:02d}{random.randint(1000, 9999)}"
        
        # Description
        ecriture_lib = random.choice(descriptions)
        
        # Entrée FEC
        entry = {
            "journal_code": journal_code,
            "journal_lib": journal_lib,
            "ecr_num": f"ECR{i+1:06d}",
            "ecr_date": ecr_date.strftime("%Y-%m-%d"),
            "compte_num": compte_num,
            "compte_lib": compte_lib,
            "comp_aux_num": "",
            "comp_aux_lib": "",
            "piece_ref": piece_ref,
            "piece_date": ecr_date.strftime("%Y-%m-%d"),
            "ecriture_lib": ecriture_lib,
            "debit_montant": debit,
            "credit_montant": credit,
            "ecriture_date": ecr_date.strftime("%Y-%m-%d"),
            "validation_date": ecr_date.strftime("%Y-%m-%d") if random.random() > 0.2 else None
        }
        
        entries.append(entry)
    
    logger.info(f"Généré {len(entries)} entrées FEC fictives")
    return entries

def generate_dummy_analysis_results(file_id: str, anomaly_count: int = 5) -> Dict[str, Any]:
    """
    Génère des résultats d'analyse fictifs
    
    Args:
        file_id: ID du fichier
        anomaly_count: Nombre d'anomalies à générer
        
    Returns:
        Un dictionnaire contenant les résultats d'analyse
    """
    anomalies = []
    
    # Générer un ensemble d'anomalies fictives
    for i in range(anomaly_count):
        anomaly = generate_dummy_anomaly(line_number=random.randint(1, 1000))
        anomalies.append(anomaly.dict())
    
    return {
        "anomalies": anomalies,
        "total_count": len(anomalies),
        "file_id": file_id,
        "analysis_duration_ms": random.uniform(1000, 5000)
    }
