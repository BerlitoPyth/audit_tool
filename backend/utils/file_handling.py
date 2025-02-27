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

ALLOWED_EXTENSIONS = {'csv', 'txt', 'xlsx', 'xls'}

def is_allowed_file(filename: str) -> bool:
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def validate_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Valide si un fichier est au format accepté (FEC ou Excel)
    
    Args:
        file: Le fichier à valider
        
    Returns:
        Un tuple (is_valid, message) indiquant si le fichier est valide
        et un message d'erreur le cas échéant
    """
    if not file.filename:
        return False, "Nom de fichier non fourni"
    
    if not is_allowed_file(file.filename):
        return False, f"Format de fichier non supporté. Formats acceptés : {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Pour les xlsx/xls, on vérifie si c'est un fichier Excel valide
    if file.filename.endswith(('.xlsx', '.xls')):
        try:
            content = await file.read(1024)  # Lire un échantillon pour validation
            await file.seek(0)  # Reset le curseur au début
            
            # Vérification minimale pour un fichier Excel (signatures de fichier)
            xlsx_signature = b'PK\x03\x04'
            xls_signature = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
            
            if file.filename.endswith('.xlsx') and not content.startswith(xlsx_signature):
                return False, "Fichier XLSX invalide ou corrompu"
            
            if file.filename.endswith('.xls') and not content.startswith(xls_signature):
                return False, "Fichier XLS invalide ou corrompu"
            
            return True, None
        except Exception as e:
            logger.error(f"Erreur lors de la validation du fichier Excel: {str(e)}")
            return False, f"Erreur lors de la validation: {str(e)}"
    
    # Pour les fichiers CSV/TXT (FEC)
    else:
        return await validate_fec_file(file)

async def save_upload_file(upload_file: UploadFile, file_id: str, base_dir: str) -> str:
    """
    Sauvegarde un fichier uploadé sur le disque
    
    Args:
        upload_file: Le fichier uploadé
        file_id: L'identifiant unique du fichier
        base_dir: Le répertoire de base pour les uploads
        
    Returns:
        Le chemin complet du fichier sauvegardé
    """
    upload_dir = os.path.join(base_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Créer un chemin pour le nouveau fichier
    file_path = os.path.join(upload_dir, f"{file_id}_{upload_file.filename}")
    
    # Lire et écrire le fichier de manière asynchrone
    try:
        # Rembobiner le fichier au début par sécurité
        await upload_file.seek(0)
        
        # Écrire le fichier sur le disque
        async with aiofiles.open(file_path, "wb") as out_file:
            # Lire le fichier par morceaux pour économiser la mémoire
            while content := await upload_file.read(1024 * 1024):  # Lire 1 MB à la fois
                await out_file.write(content)
                
        logger.info(f"Fichier sauvegardé: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier {upload_file.filename}: {str(e)}", exc_info=e)
        # Si le fichier existe déjà partiellement, le supprimer
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


async def validate_fec_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Valide si un fichier est au format FEC (Format d'Échange Comptable)
    
    Args:
        file: Le fichier à valider
        
    Returns:
        Un tuple (is_valid, message) indiquant si le fichier est valide
        et un message d'erreur le cas échéant
    """
    # Pour l'instant, nous acceptons tous les fichiers comme valides
    # Cette fonction devrait être implémentée avec une véritable logique de validation
    return True, None


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


async def read_excel_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Lit un fichier Excel et convertit son contenu en liste de dictionnaires
    
    Args:
        file_path: Chemin du fichier Excel
        
    Returns:
        Liste de dictionnaires représentant les lignes du fichier
    """
    try:
        import pandas as pd
        
        # Détecter le format (xlsx/xls) et lire avec pandas
        df = pd.read_excel(file_path)
        
        # Nettoyer les noms de colonnes (espaces, caractères spéciaux)
        df.columns = [str(col).strip() for col in df.columns]
        
        # Convertir en liste de dictionnaires
        records = df.to_dict('records')
        
        logger.info(f"Fichier Excel chargé: {len(records)} lignes")
        return records
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier Excel {file_path}: {str(e)}")
        raise

async def read_file_content(file_path: str) -> List[Dict[str, Any]]:
    """
    Lit le contenu d'un fichier selon son format (CSV, Excel, ...)
    et le convertit en liste de dictionnaires
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        Liste de dictionnaires représentant les données du fichier
    """
    if file_path.lower().endswith(('.xlsx', '.xls')):
        return await read_excel_file(file_path)
    else:
        return await read_fec_file(file_path)

async def delete_file(file_path: str) -> bool:
    """
    Supprime un fichier du système de fichiers
    
    Args:
        file_path: Le chemin du fichier à supprimer
        
    Returns:
        True si la suppression a réussi, False sinon
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Fichier supprimé: {file_path}")
            return True
        logger.warning(f"Fichier introuvable lors de la suppression: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}", exc_info=e)
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