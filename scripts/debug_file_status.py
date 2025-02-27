#!/usr/bin/env python
"""
Script de diagnostic pour vérifier l'état d'un fichier et ses analyses associées.
Utile pour déboguer les problèmes liés aux résultats d'analyse manquants.
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pprint import pprint

# Ajouter le projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings
from backend.services.analysis_service import get_analysis_service

settings = get_settings()

async def check_file_status(file_id: str):
    """
    Vérifie le statut d'un fichier et de ses analyses associées
    
    Args:
        file_id: Identifiant du fichier à vérifier
    """
    print(f"\n=== Diagnostic pour le fichier {file_id} ===\n")
    
    # Récupération des chemins
    uploads_dir = os.path.join(settings.DATA_DIR, "uploads")
    jobs_dir = os.path.join(settings.DATA_DIR, "jobs")
    results_dir = os.path.join(settings.DATA_DIR, "results")
    
    # 1. Vérifier si le fichier existe
    metadata_path = os.path.join(uploads_dir, f"{file_id}_meta.json")
    file_exists = os.path.exists(metadata_path)
    
    print(f"1. Fichier enregistré: {'OUI' if file_exists else 'NON'}")
    print(f"   Chemin des métadonnées: {metadata_path}")
    
    if not file_exists:
        print("\n⚠️  Le fichier n'existe pas dans le système!")
        print("   Vérifiez que vous utilisez le bon ID de fichier")
        print("   Vous pouvez lister les fichiers disponibles avec: python scripts/debug_file_status.py --list-files")
        return
    
    # 2. Charger les métadonnées du fichier
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    print(f"\n2. Information sur le fichier:")
    print(f"   Nom: {metadata['filename']}")
    print(f"   Taille: {metadata['file_size']} octets")
    print(f"   Date d'upload: {metadata['upload_timestamp']}")
    print(f"   Description: {metadata.get('description', 'N/A')}")
    
    # 3. Vérifier si le fichier physique existe
    file_path = metadata.get("file_path", "")
    file_physical_exists = os.path.exists(file_path)
    print(f"\n3. Fichier physique: {'OUI' if file_physical_exists else 'NON'}")
    print(f"   Chemin: {file_path}")
    
    if not file_physical_exists:
        print("\n⚠️  Le fichier physique est manquant! Vous devrez probablement uploader à nouveau.")
    
    # 4. Vérifier les analyses associées
    analyses = metadata.get("analyses", [])
    print(f"\n4. Analyses associées: {len(analyses)}")
    
    if not analyses:
        print("\n⚠️  Aucune analyse n'a été lancée pour ce fichier!")
        print("   Utilisez POST /api/v1/analysis/start pour démarrer une analyse")
        return
    
    # 5. Examiner chaque analyse
    for i, analysis in enumerate(analyses):
        job_id = analysis.get("job_id")
        print(f"\n   Analyse #{i+1}:")
        print(f"   - ID: {job_id}")
        print(f"   - Type: {analysis.get('analysis_type', 'N/A')}")
        print(f"   - Date: {analysis.get('timestamp', 'N/A')}")
        
        # Vérifier le statut du job
        job_path = os.path.join(jobs_dir, f"{job_id}.json")
        if os.path.exists(job_path):
            with open(job_path, "r", encoding="utf-8") as f:
                job_data = json.load(f)
                
            print(f"   - Statut: {job_data.get('status', 'N/A')}")
            print(f"   - Progression: {job_data.get('progress', 0)}%")
            
            if job_data.get("error"):
                print(f"   - Erreur: {job_data.get('error')}")
        else:
            print(f"   - Fichier de job manquant: {job_path}")
    
    # 6. Vérifier les résultats d'analyse
    result_path = os.path.join(results_dir, f"{file_id}.json")
    result_exists = os.path.exists(result_path)
    
    print(f"\n5. Résultats d'analyse: {'OUI' if result_exists else 'NON'}")
    print(f"   Chemin attendu: {result_path}")
    
    if not result_exists:
        print("\n⚠️  Le fichier de résultats est manquant!")
        
        # Recommandations
        if any(job_data.get("status") == "failed" for job_data in analyses):
            print("   Une analyse a échoué. Vérifiez les erreurs ci-dessus et relancez l'analyse.")
        elif any(job_data.get("status") == "processing" for job_data in analyses):
            print("   Une analyse est encore en cours. Attendez qu'elle se termine.")
        else:
            print("   Toutes les analyses semblent terminées mais aucun résultat n'est disponible.")
            print("   Il y a probablement eu une erreur lors de la sauvegarde des résultats.")
            print("   Relancez une analyse avec POST /api/v1/analysis/start")
    else:
        # 7. Afficher un résumé des résultats
        with open(result_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        
        print(f"\n6. Résumé des résultats:")
        print(f"   Nombre total d'écritures: {results.get('total_entries', 'N/A')}")
        print(f"   Nombre d'anomalies: {results.get('anomaly_count', 'N/A')}")
        print(f"   Date d'analyse: {results.get('analysis_timestamp', 'N/A')}")
        
        if results.get("anomalies"):
            # Grouper par type d'anomalie
            anomaly_types = {}
            for anomaly in results.get("anomalies", []):
                anomaly_type = anomaly.get("type", "unknown")
                if anomaly_type not in anomaly_types:
                    anomaly_types[anomaly_type] = 0
                anomaly_types[anomaly_type] += 1
            
            print("\n   Types d'anomalies détectées:")
            for anomaly_type, count in anomaly_types.items():
                print(f"   - {anomaly_type}: {count}")

async def list_files():
    """Liste tous les fichiers disponibles"""
    analysis_service = get_analysis_service()
    files = await analysis_service.list_files(page=1, page_size=100)
    
    print("\n=== Fichiers disponibles ===\n")
    
    if not files:
        print("Aucun fichier trouvé.")
        return
    
    print(f"{'ID':36} | {'Nom':30} | {'Taille':10} | {'Date d\\'upload':20}")
    print("-" * 100)
    
    for file in files:
        upload_time = file.upload_timestamp.strftime("%Y-%m-%d %H:%M:%S") if file.upload_timestamp else "N/A"
        print(f"{file.file_id} | {file.filename[:30]:30} | {file.size_bytes:10} | {upload_time:20}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Diagnostic pour l'état d'un fichier et ses analyses")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file-id", help="ID du fichier à vérifier")
    group.add_argument("--list-files", action="store_true", help="Lister tous les fichiers disponibles")
    
    args = parser.parse_args()
    
    if args.list_files:
        asyncio.run(list_files())
    else:
        asyncio.run(check_file_status(args.file_id))

if __name__ == "__main__":
    main()