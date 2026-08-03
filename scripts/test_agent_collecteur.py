from src.agents.collecteur import agent_collecteur

if __name__ == "__main__":
    # Test avec 3 scénarios
    state_initial = {
        "scenario_ids": [1, 8, 11],
        "model_names": ["llama3.1:8b", "mistral:7b"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    state_apres = agent_collecteur(state_initial)

    print(f"\n--- RÉSULTAT ---")
    print(f"Scénarios collectés : {len(state_apres['scenarios'])}")
    for s in state_apres["scenarios"]:
        print(f"  - [{s['id']}] {s['nom_cas_usage']} ({s['departement']}) — {len(s['chunks_rag'])} chunks")
    if state_apres["erreurs"]:
        print(f"Erreurs : {state_apres['erreurs']}")