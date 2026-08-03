from src.agents.graph import benchmark_graph

if __name__ == "__main__":

    # Configuration du benchmark
    config = {
        "scenario_ids": [1, 11],
        "model_names": ["llama3.1:8b", "mistral:7b"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    print("DÉMARRAGE DU BENCHMARK VIA LANGGRAPH")
    print(f"Scénarios : {config['scenario_ids']}")
    print(f"Modèles   : {config['model_names']}")
    print(f"Total     : {len(config['scenario_ids']) * len(config['model_names'])} exécutions\n")

    # Lancement du graphe en une seule ligne
    resultat = benchmark_graph.invoke(config)

    # Affichage du rapport final
    rapport = resultat.get("rapport", {})
    print(f"\nBenchmark terminé.")
    print(f"  Modèles testés  : {rapport.get('nb_modeles', 0)}")
    print(f"  Scénarios       : {rapport.get('nb_scenarios', 0)}")

    if resultat.get("erreurs"):
        print(f"\nErreurs : {resultat['erreurs']}")