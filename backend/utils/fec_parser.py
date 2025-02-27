import csv
import codecs
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

class FECParser:
    """
    Classe pour parser les fichiers FEC (Format d'Echange Comptable)
    """
    
    def __init__(self, file_path: str):
        """
        Initialise le parser FEC
        
        Args:
            file_path: Chemin du fichier FEC à parser
        """
        self.file_path = file_path
        self.encoding = self._detect_encoding()
        self.delimiter = self._detect_delimiter()
        
    def _detect_encoding(self) -> str:
        """
        Détecte l'encodage du fichier
        
        Returns:
            L'encodage détecté
        """
        encodings = ['utf-8', 'ISO-8859-1', 'windows-1252']
        
        for enc in encodings:
            try:
                with codecs.open(self.file_path, 'r', encoding=enc) as f:
                    f.read(1024)
                logger.info(f"Encodage détecté: {enc}")
                return enc
            except UnicodeDecodeError:
                continue
        
        logger.warning("Encodage non détecté, utilisation de utf-8 par défaut")
        return 'utf-8'
    
    def _detect_delimiter(self) -> str:
        """
        Détecte le délimiteur du fichier
        
        Returns:
            Le délimiteur détecté
        """
        with codecs.open(self.file_path, 'r', encoding=self.encoding) as f:
            sample = f.read(1024)
            
        # Vérifier les délimiteurs courants
        delimiters = [';', ',', '\t', '|']
        counts = {delim: sample.count(delim) for delim in delimiters}
        
        # Trouver le délimiteur avec le plus grand nombre d'occurrences
        max_delim = max(counts.items(), key=lambda x: x[1])
        
        # Si le délimiteur est peu présent, essayer avec csv.Sniffer
        if max_delim[1] < 5:
            try:
                dialect = csv.Sniffer().sniff(sample)
                logger.info(f"Délimiteur détecté via Sniffer: {dialect.delimiter}")
                return dialect.delimiter
            except:
                pass
        
        logger.info(f"Délimiteur détecté: {max_delim[0]}")
        return max_delim[0]
    
    def parse(self, chunksize: int = 10000) -> List[Dict[str, Any]]:
        """
        Parse le fichier FEC
        
        Args:
            chunksize: Taille des lots pour traiter des fichiers volumineux
            
        Returns:
            Liste de dictionnaires représentant les entrées FEC
        """
        logger.info(f"Parsing du fichier FEC {self.file_path} (encodage: {self.encoding}, délimiteur: {self.delimiter})")
        
        # Utiliser pandas pour lire efficacement les fichiers volumineux
        try:
            chunks = pd.read_csv(
                self.file_path,
                sep=self.delimiter,
                encoding=self.encoding,
                chunksize=chunksize,
                low_memory=False,
                dtype=str,  # Tout lire comme des chaînes pour éviter les inférences de type
                na_filter=False  # Pas de conversion des valeurs manquantes
            )
            
            result = []
            total_rows = 0
            
            for chunk in chunks:
                # Nettoyer les noms de colonnes
                chunk.columns = [col.strip() for col in chunk.columns]
                
                # Convertir certaines colonnes si nécessaire
                numeric_columns = ['Debit', 'Credit', 'Montantdevise']
                for col in numeric_columns:
                    if col in chunk.columns:
                        # Remplacer les virgules par des points pour les valeurs décimales
                        chunk[col] = chunk[col].str.replace(',', '.', regex=False)
                        chunk[col] = pd.to_numeric(chunk[col], errors='coerce').fillna(0)
                
                # Convertir les données en dictionnaires
                chunk_dict = chunk.to_dict('records')
                result.extend(chunk_dict)
                
                total_rows += len(chunk_dict)
                logger.info(f"Chargé {len(chunk_dict)} lignes, total: {total_rows}")
                
                # Pour les fichiers énormes, limiter le nombre de lignes traitées
                if total_rows >= 1000000:
                    logger.warning("Limite de 1 million de lignes atteinte, traitement partiel")
                    break
            
            logger.info(f"Parsing terminé: {total_rows} lignes chargées")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing du fichier FEC: {str(e)}", exc_info=e)
            raise
