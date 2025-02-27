#!/usr/bin/env python
"""
Script pour analyser les performances des modèles de détection d'anomalies
"""
import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Any

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings
from backend.training.model_registry import get_model_registry
from backend.models.my_fec_generator import MyFECGenerator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()


def load_detection_stats() -> pd.DataFrame:
    """Charge les statistiques de détection depuis le fichier jsonl"""
    stats_file = os.path.join(settings.DATA_DIR, "stats", "detection_stats.jsonl")
    
    if not os.path.exists(stats_file):
        logger.warning(f"Fichier de statistiques non trouvé: {stats_file}")
        return pd.DataFrame()
    
    # Charger les lignes en tant qu'objets JSON
    stats = []
    with open(stats_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                stats.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                logger.warning(f"Ligne invalide ignorée dans {stats_file}")
    
    if not stats:
        return pd.DataFrame()
    
    # Convertir en DataFrame pour faciliter l'analyse
    df = pd.DataFrame(stats)
    
    # Convertir les timestamps en objets datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df


def analyse_model_versions(stats: pd.DataFrame) -> None:
    """Analyse les performances par version du modèle"""
    if stats.empty or 'model_version' not in stats.columns:
        logger.warning("Pas de données suffisantes pour analyser les versions de modèles")
        return
    
    # Filtrer pour ne garder que les détections ML
    ml_stats = stats[stats['method'] == 'ml']
    
    if ml_stats.empty:
        logger.warning("Pas de détections ML dans les statistiques")
        return
    
    # Grouper par version de modèle
    version_stats = ml_stats.groupby('model_version').agg({
        'num_entries': 'sum',
        'num_anomalies': 'sum',
        'anomaly_rate': 'mean',
        'execution_time': 'mean',
        'entries_per_second': 'mean',
        'timestamp': ['min', 'max', 'count']
    }).reset_index()
    
    # Renommer les colonnes
    version_stats.columns = ['model_version', 'total_entries', 'total_anomalies', 'avg_anomaly_rate', 
                             'avg_execution_time', 'avg_entries_per_second', 
                             'first_used', 'last_used', 'usage_count']
    
    # Afficher les résultats
    print("\n=== PERFORMANCES PAR VERSION DE MODÈLE ===")
    for _, row in version_stats.iterrows():
        print(f"\nVersion: {row['model_version']}")
        print(f"  Utilisations: {int(row['usage_count'])}")
        print(f"  Période: {row['first_used'].strftime('%Y-%m-%d')} au {row['last_used'].strftime('%Y-%m-%d')}")
        print(f"  Entrées analysées: {int(row['total_entries'])}")
        print(f"  Anomalies détectées: {int(row['total_anomalies'])}")
        print(f"  Taux d'anomalie moyen: {row['avg_anomaly_rate']:.2%}")
        print(f"  Temps d'exécution moyen: {row['avg_execution_time']:.2f}s")
        print(f"  Vitesse moyenne: {row['avg_entries_per_second']:.1f} entrées/s")
    
    # Comparer les performances des méthodes ML vs règles
    print("\n=== COMPARAISON ML vs RÈGLES ===")
    method_stats = stats.groupby('method').agg({
        'num_entries': 'sum',
        'num_anomalies': 'sum',
        'anomaly_rate': 'mean',
        'execution_time': 'mean',
        'entries_per_second': 'mean',
        'timestamp': 'count'
    }).reset_index()
    
    for _, row in method_stats.iterrows():
        method_name = "Machine Learning" if row['method'] == 'ml' else "Règles prédéfinies"
        print(f"\nMéthode: {method_name}")
        print(f"  Utilisations: {int(row['timestamp'])}")
        print(f"  Entrées analysées: {int(row['num_entries'])}")
        print(f"  Anomalies détectées: {int(row['num_anomalies'])}")
        print(f"  Taux d'anomalie moyen: {row['anomaly_rate']:.2%}")
        print(f"  Temps d'exécution moyen: {row['execution_time']:.2f}s")
        print(f"  Vitesse moyenne: {row['entries_per_second']:.1f} entrées/s")


def compare_model_metrics() -> None:
    """Compare les métriques des différents modèles enregistrés"""
    registry = get_model_registry()
    models = registry.list_models()
    
    if not models:
        logger.warning("Aucun modèle enregistré trouvé")
        return
    
    # Extraire les métriques
    metrics_data = []
    for model in models:
        version = model.get("version", "inconnu")
        metrics = model.get("metrics", {})
        created_at = model.get("created_at", "")
        
        row = {
            "version": version,
            "created_at": created_at,
            "is_active": model.get("is_active", False)
        }
        
        # Ajouter toutes les métriques disponibles
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                row[key] = value
        
        metrics_data.append(row)
    
    if not metrics_data:
        logger.warning("Pas de métriques disponibles dans les modèles")
        return
    
    # Convertir en DataFrame
    metrics_df = pd.DataFrame(metrics_data)
    
    if "created_at" in metrics_df.columns:
        metrics_df["created_at"] = pd.to_datetime(metrics_df["created_at"])
        metrics_df = metrics_df.sort_values("created_at", ascending=False)
    
    # Afficher les métriques
    print("\n=== MÉTRIQUES DES MODÈLES ENREGISTRÉS ===")
    
    # Filtrer les colonnes pertinentes
    display_cols = ["version", "created_at", "is_active", 
                    "training_time", "training_samples"]
    
    # Ajouter les colonnes de métriques disponibles
    for col in metrics_df.columns:
        if "_anomaly_rate" in col or "_score_mean" in col or "_score_std" in col:
            display_cols.append(col)
    
    # Sélectionner uniquement les colonnes disponibles
    available_cols = [col for col in display_cols if col in metrics_df.columns]
    
    # Afficher le tableau
    print(metrics_df[available_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    
    active_model = registry.get_active_model_info()
    if active_model:
        print(f"\nModèle actif : {active_model['version']}")
    else:
        print("\nAucun modèle actif défini")


def create_performance_visualizations(stats: pd.DataFrame) -> None:
    """Crée des visualisations pour comparer les performances"""
    if stats.empty:
        logger.warning("Pas de données pour créer des visualisations")
        return
    
    # Créer le répertoire pour les visualisations
    viz_dir = os.path.join(settings.DATA_DIR, "visualizations")
    os.makedirs(viz_dir, exist_ok=True)
    
    # Convertir timestamp en date
    if "timestamp" in stats.columns:
        stats["date"] = stats["timestamp"].dt.date
    
    try:
        # 1. Évolution du taux d'anomalies dans le temps
        plt.figure(figsize=(10, 6))
        
        ml_stats = stats[stats["method"] == "ml"]
        rule_stats = stats[stats["method"] == "rules"]
        
        if not ml_stats.empty:
            ml_by_date = ml_stats.groupby("date")["anomaly_rate"].mean().reset_index()
            plt.plot(ml_by_date["date"], ml_by_date["anomaly_rate"], 
                     label="ML", marker="o", color="blue")
        
        if not rule_stats.empty:
            rule_by_date = rule_stats.groupby("date")["anomaly_rate"].mean().reset_index()
            plt.plot(rule_by_date["date"], rule_by_date["anomaly_rate"], 
                     label="Règles", marker="x", color="red", linestyle="--")
        
        plt.title("Évolution du taux d'anomalies détectées")
        plt.xlabel("Date")
        plt.ylabel("Taux d'anomalies")
        plt.ylim(bottom=0)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        viz_path = os.path.join(viz_dir, "anomaly_rate_evolution.png")
        plt.savefig(viz_path)
        logger.info(f"Graphique sauvegardé dans {viz_path}")
        
        # 2. Comparaison des performances (vitesse)
        plt.figure(figsize=(10, 6))
        
        if "method" in stats.columns and "entries_per_second" in stats.columns:
            method_perf = stats.groupby("method")["entries_per_second"].agg(["mean", "std"]).reset_index()
            
            plt.bar(method_perf["method"], method_perf["mean"], 
                   yerr=method_perf["std"], capsize=10, 
                   color=["blue", "red"] if len(method_perf) > 1 else ["blue"])
            
            plt.title("Comparaison des performances de détection")
            plt.xlabel("Méthode")
            plt.ylabel("Entrées traitées par seconde")
            plt.grid(True, axis="y", linestyle="--", alpha=0.7)
            
            # Ajouter les valeurs sur les barres
            for i, v in enumerate(method_perf["mean"]):
                plt.text(i, v + 0.5, f"{v:.1f}", ha="center")
            
            viz_path = os.path.join(viz_dir, "performance_comparison.png")
            plt.savefig(viz_path)
            logger.info(f"Graphique sauvegardé dans {viz_path}")
        
        # Afficher les chemins des visualisations
        print(f"\nVisualisations sauvegardées dans {viz_dir}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la création des visualisations: {str(e)}")
        import traceback
        traceback.print_exc()


def generate_performance_report() -> None:
    """Génère un rapport complet sur les performances des modèles"""
    stats = load_detection_stats()
    
    print("\n" + "="*50)
    print("RAPPORT DE PERFORMANCES DES MODÈLES DE DÉTECTION")
    print("="*50)
    
    if stats.empty:
        print("\nAucune donnée de performance disponible.")
        print("Exécutez des analyses avec le détecteur pour collecter des statistiques.")
        return
    
    print(f"\nDonnées de {len(stats)} exécutions de détection")
    print(f"Période: {stats['timestamp'].min().strftime('%Y-%m-%d')} au {stats['timestamp'].max().strftime('%Y-%m-%d')}")
    
    # Analyser les versions de modèles
    analyse_model_versions(stats)
    
    # Comparer les métriques d'entraînement
    compare_model_metrics()
    
    # Créer des visualisations
    create_performance_visualizations(stats)
    
    print("\n" + "="*50)
    print("FIN DU RAPPORT")
    print("="*50)


def evaluate_model(args):
    """Évalue un modèle sur un jeu de test généré"""
    from backend.models.trained_detector import TrainedDetector
    import asyncio
    
    # Utiliser la version spécifiée ou le modèle actif
    detector = TrainedDetector(model_version=args.version)
    
    # Vérifier que le modèle ML est chargé
    if not detector._use_ml_models:
        logger.error("Modèle ML non disponible, impossible de procéder à l'évaluation")
        return
    
    # Générer des données de test
    logger.info(f"Génération de {args.count} entrées de test avec {args.anomaly_rate*100}% d'anomalies")
    generator = MyFECGenerator(
        company_name="TEST_EVALUATION",
        anomaly_rate=args.anomaly_rate
    )
    
    test_entries = generator.generate_entries(count=args.count)
    
    # Détecter les anomalies
    logger.info(f"Détection d'anomalies sur {len(test_entries)} entrées avec le modèle {detector.model_version}")
    anomalies = asyncio.run(detector.detect_anomalies(test_entries))
    
    # Calculer les statistiques
    anomaly_count = len(anomalies)
    anomaly_rate = anomaly_count / len(test_entries) if test_entries else 0
    
    print(f"\nRésultats de l'évaluation du modèle {detector.model_version}:")
    print(f"  Entrées analysées: {len(test_entries)}")
    print(f"  Anomalies injectées: ~{int(args.count * args.anomaly_rate)} ({args.anomaly_rate:.1%})")
    print(f"  Anomalies détectées: {anomaly_count} ({anomaly_rate:.1%})")
    
    # Répartition par type d'anomalie
    anomaly_types = {}
    for anomaly in anomalies:
        anomaly_type = anomaly.type.value
        if anomaly_type not in anomaly_types:
            anomaly_types[anomaly_type] = 0
        anomaly_types[anomaly_type] += 1
    
    print("\nRépartition par type d'anomalie:")
    for anomaly_type, count in anomaly_types.items():
        print(f"  {anomaly_type}: {count} ({count/anomaly_count:.1%})")


def parse_args():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Analyse les performances des modèles de détection d'anomalies")
    
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande "report" - Génère un rapport complet
    report_parser = subparsers.add_parser("report", help="Génère un rapport de performances complet")
    
    # Commande "evaluate" - Évalue un modèle sur des données générées
    eval_parser = subparsers.add_parser("evaluate", help="Évalue un modèle sur un jeu de test généré")
    eval_parser.add_argument("--version", type=str, help="Version du modèle à évaluer (utilise le modèle actif par défaut)")
    eval_parser.add_argument("--count", type=int, default=1000, help="Nombre d'entrées à générer")
    eval_parser.add_argument("--anomaly-rate", type=float, default=0.1, help="Taux d'anomalies à injecter")
    
    # Commande "metrics" - Affiche uniquement les métriques
    metrics_parser = subparsers.add_parser("metrics", help="Affiche les métriques des modèles")
    
    return parser.parse_args()


def main():
    """Fonction principale"""
    args = parse_args()
    
    if args.command == "report" or args.command is None:
        generate_performance_report()
    elif args.command == "evaluate":
        evaluate_model(args)
    elif args.command == "metrics":
        compare_model_metrics()
    else:
        print("Commande non reconnue. Utilisez --help pour voir les options disponibles.")


if __name__ == "__main__":
    main()