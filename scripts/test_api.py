#!/usr/bin/env python
"""Script pour tester l'API d'audit"""
import os
import sys
import requests
import json
import time
from datetime import datetime
import argparse
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings

settings = get_settings()
BASE_URL = f"http://{settings.HOST}:{settings.PORT}{settings.API_V1_STR}"


def test_health():
    """Teste les endpoints de healthcheck"""
    print("\n=== Test des endpoints de santé ===")
    
    # Test /healthz/live
    response = requests.get(f"{BASE_URL}/healthz/live")
    print(f"Liveness check: {response.status_code}")
    print(response.json())
    
    # Test /healthz/ready
    response = requests.get(f"{BASE_URL}/healthz/ready")
    print(f"Readiness check: {response.status_code}")
    print(response.json())
    
    # Test /healthz/health
    response = requests.get(f"{BASE_URL}/healthz/health")
    print(f"Health check: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_file_upload(file_path: str):
    """Teste l'upload de fichier"""
    print("\n=== Test de l'upload de fichier ===")
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{BASE_URL}/analysis/upload",
            files=files
        )
    
    print(f"Upload status: {response.status_code}")
    result = response.json()
    print(json.dumps(result, indent=2))
    return result.get('file_id')


def test_analysis(file_id: str):
    """Teste l'analyse d'un fichier"""
    print("\n=== Test de l'analyse de fichier ===")
    
    # Démarrer l'analyse
    response = requests.post(
        f"{BASE_URL}/analysis/start",
        json={
            "file_id": file_id,
            "analysis_type": "standard"
        }
    )
    
    print(f"Analysis start status: {response.status_code}")
    job = response.json()
    job_id = job['job_id']
    
    # Attendre les résultats
    print("\nAttente des résultats...")
    max_attempts = 30
    for i in range(max_attempts):
        response = requests.get(f"{BASE_URL}/analysis/status/{job_id}")
        status = response.json()
        
        print(f"Progress: {status['progress']}%")
        
        if status['status'] in ['completed', 'failed']:
            break
            
        time.sleep(1)
    
    # Récupérer les résultats
    if status['status'] == 'completed':
        response = requests.get(f"{BASE_URL}/analysis/results/{file_id}")
        results = response.json()
        print("\nRésultats de l'analyse:")
        print(f"Nombre d'anomalies: {results['anomaly_count']}")
        print("\nDétail des anomalies:")
        for anomaly in results['anomalies']:
            print(f"\n- Type: {anomaly['type']}")
            print(f"  Description: {anomaly['description']}")
            print(f"  Confiance: {anomaly['confidence_score']:.2%}")
            print(f"  Lignes concernées: {anomaly['line_numbers']}")
    else:
        print(f"\nAnalyse terminée avec erreur: {status['error']}")


def test_model_management():
    """Teste la gestion des modèles"""
    print("\n=== Test de la gestion des modèles ===")
    
    # Liste des modèles
    response = requests.get(f"{BASE_URL}/models/list")
    print(f"Liste des modèles status: {response.status_code}")
    models = response.json()
    print(json.dumps(models, indent=2))
    
    # Modèle actif
    response = requests.get(f"{BASE_URL}/models/active")
    print(f"\nModèle actif status: {response.status_code}")
    if response.status_code == 200:
        active_model = response.json()
        print(json.dumps(active_model, indent=2))


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Test de l'API d'audit")
    parser.add_argument('--file', type=str, help='Chemin vers un fichier FEC à analyser')
    args = parser.parse_args()
    
    try:
        # Test healthcheck
        test_health()
        
        # Test modèles
        test_model_management()
        
        # Si un fichier est fourni, tester l'upload et l'analyse
        if args.file:
            if not os.path.exists(args.file):
                print(f"\nErreur: Le fichier {args.file} n'existe pas")
                return
            
            file_id = test_file_upload(args.file)
            if file_id:
                test_analysis(file_id)
        
    except requests.exceptions.ConnectionError:
        print(f"\nErreur: Impossible de se connecter à l'API ({BASE_URL})")
        print("Assurez-vous que l'API est démarrée")
    except Exception as e:
        print(f"\nErreur inattendue: {str(e)}")


if __name__ == "__main__":
    main()