import os
import shutil
import logging
import csv
import aiofiles
import asyncio
import tempfile
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from fastapi import UploadFile
import pandas as pd
import io

logger = logging.getLogger(__name__)

# Taille de bloc pour la lecture des fichiers volumineux (16 Mo)
CHUNK_SIZE = 16 * 1024 * 1024

# Liste des en-têtes attendus pour un fichier FEC
FEC_EXPECTED_HEADERS = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", 
    "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib", 
    "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit", 
    "EcritureLet", "DateLet", "ValidDate", "Montantdevise", 
    "Idevise"
]


async def save_upload_file(file: UploadFile, file_id: str, target_dir: str) -> str:
    """
    Sauvegarde un fichier uploadé avec gestion des fichiers volumineux.
    Retourne le chemin du fichier sauvegardé.
    """
    # Création d'un nom de fichier unique
    file_extension = os.path.splitext(file.filename)[1]
    target_path = os.path.join(target_dir, f"{file_id}{file_extension}")
    
    # Création du dossier cible si nécessaire
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    try:
        # Ouverture du fichier cible en mode binaire
        async with aiofiles.open(target_path, 'wb') as out_file:
            # Lecture par blocs pour éviter de charger l'intégralité du fichier en mémoire
            while content := await file.read(CHUNK_SIZE):
                await out_file.write(content)
        
        logger.info(f"Fichier sauvegardé: {target_path}")
        return target_path
    
    except Exception as e:
        # Suppression du fichier partiellement écrit en cas d'erreur
        if os.path.exists(target_path):
            os.remove(target_path)
        logger.error(f"Erreur lors de la sauvegarde du fichier: {str(e)}")
        raise


async def validate_fec_file(file: UploadFile) -> Tuple[bool, str]:
    """
    Valide qu'un fichier est au format FEC (Format d'Échange Comptable).
    Retourne un tuple (est_valide, message).
    """
    # Réinitialiser la position du fichier
    await file.seek(0)
    
    try:
        # Lire une partie du début du fichier
        sample = await file.read(CHUNK_SIZE)
        await file.seek(0)  # Réinitialiser pour les utilisations futures
        
        # Détecter l'encodage (UTF-8, ISO-8859-1, etc.)
        encoding = 'utf-8'  # Par défaut
        try:
            sample_text = sample.decode(encoding)
        except UnicodeDecodeError:
            # Essayer avec un autre encodage courant pour les fichiers FEC
            encoding = 'ISO-8859-1'
            try:
                sample_text = sample.decode(encoding)
            except UnicodeDecodeError:
                return False, "Format de fichier non reconnu: problème d'encodage"
        
        # Détecter le délimiteur (tab, point-virgule, etc.)
        dialect = csv.Sniffer().sniff(sample_text.split('\n')[0])
        delimiter = dialect.delimiter
        
        # Lire les en-têtes
        buffer = io.StringIO(sample_text)
        reader = csv.reader(buffer, delimiter=delimiter)
        headers = next(reader, [])
        
        # Normaliser les en-têtes pour la comparaison
        normalized_headers = [h.strip().lower() for h in headers]
        expected_headers_lower = [h.lower() for h in FEC_EXPECTED_HEADERS]
        
        # Vérifier si les en-têtes essentiels sont présents
        missing_essential = []
        essential_headers = ["JournalCode", "EcritureNum", "EcritureDate", "CompteNum", "Debit", "Credit"]
        essential_headers_lower = [h.lower() for h in essential_headers]
        
        for header in essential_headers_lower:
            if not any(header in h for h in normalized_headers):
                missing_essential.append(header)
        
        if missing_essential:
            return False, f"En-têtes essentiels manquants: {', '.join(missing_essential)}"
        
        # Vérifier quelques lignes pour la validité des données
        valid_lines = 0
        invalid_lines = []
        
        for i, row in enumerate(reader):
            if i >= 10:  # Vérifier les 10 premières lignes
                break
                
            if len(row) < 5:  # Au moins 5 colonnes pour un FEC minimal
                invalid_lines.append(i + 2)  # +2 car i commence à 0 et on a déjà lu l'en-tête
                continue
                
            valid_lines += 1
        
        if valid_lines == 0:
            return False, "Aucune ligne de données valide trouvée"
            
        if invalid_lines:
            if len(invalid_lines) <= 3:
                return False, f"Lignes invalides détectées: {', '.join(map(str, invalid_lines))}"
            else:
                return False, f"Plusieurs lignes invalides détectées ({len(invalid_lines)} sur 10)"
        
        return True, "Fichier FEC valide"
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation du fichier FEC: {str(e)}")
        return False, f"Erreur de validation: {str(e)}"


async def read_fec_file(file_path: str, batch_size: int = 10000) -> List[Dict[str, Any]]:
    """
    Lit un fichier FEC par lots pour gérer les fichiers volumineux.
    Retourne les entrées du fichier FEC.
    """
    result = []
    
    try:
        # Détecter l'encodage et le délimiteur
        encoding = None
        delimiter = None
        
        # Essayer d'abord avec utf-8
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(1024)
                encoding = 'utf-8'
        except UnicodeDecodeError:
            # Essayer avec ISO-8859-1
            with open(file_path, 'r', encoding='ISO-8859-1') as f:
                sample = f.read(1024)
                encoding = 'ISO-8859-1'
        
        # Détecter le délimiteur
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except:
            # Délimiteurs courants pour les FEC
            for delim in [';', ',', '\t']:
                if delim in sample:
                    delimiter = delim
                    break
            if not delimiter:
                delimiter = ';'  # Par défaut pour les FEC
        
        # Utiliser pandas pour la lecture par lots (optimisé pour les fichiers volumineux)
        # Créer un générateur de lots
        chunks = pd.read_csv(
            file_path, 
            sep=delimiter, 
            encoding=encoding, 
            chunksize=batch_size,
            low_memory=True,
            dtype=str  # Pour éviter les inférences de type qui peuvent être lentes
        )
        
        # Lire chaque lot et convertir en dictionnaires
        total_rows = 0
        for chunk in chunks:
            # Convertir les noms de colonnes pour correspondre aux schémas
            chunk.columns = [col.strip() for col in chunk.columns]
            
            # Convertir les valeurs numériques
            for col in ['Debit', 'Credit', 'Montantdevise']:
                if col in chunk.columns:
                    chunk[col] = pd.to_numeric(chunk[col], errors='coerce').fillna(0)
            
            # Ajouter ce lot aux résultats
            chunk_dicts = chunk.to_dict('records')
            result.extend(chunk_dicts)
            
            total_rows += len(chunk_dicts)
            logger.info(f"Lot chargé: {len(chunk_dicts)} lignes, total: {total_rows}")
            
            # Pour des fichiers extrêmement volumineux, on pourrait limiter le nombre total de lignes
            if total_rows >= 1000000:  # Par exemple, limiter à 1 million de lignes
                logger.warning(f"Limite de 1 million de lignes atteinte. Traitement partiel du fichier.")
                break
        
        logger.info(f"Fichier FEC chargé: {total_rows} lignes au total")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier FEC: {str(e)}")
        raise


async def delete_file(file_path: str) -> bool:
    """Supprime un fichier physique"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")
        return False


async def get_file_size(file_path: str) -> int:
    """Retourne la taille d'un fichier en octets"""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la taille du fichier {file_path}: {str(e)}")
        return 0


async def create_temp_file() -> Tuple[str, BinaryIO]:
    """Crée un fichier temporaire et retourne son chemin et son descripteur"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.tmp')
    temp_file = os.fdopen(temp_fd, 'wb')
    return temp_path, temp_file


async def stream_file(file_path: str):
    """
    Générateur asynchrone pour streamer un fichier par morceaux.
    Utile pour les téléchargements de fichiers volumineux.
    """
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(CHUNK_SIZE):
            yield chunk