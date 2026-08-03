from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur

if __name__ == "__main__":
    # On teste avec 1 seul scénario et 1 seul modèle pour aller vite
    state_initial = {
        "scenario_ids": [1],
        "model_names": ["llama3.1:8b"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    print("=== COLLECTEUR ===")
    state = agent_collecteur(state_initial)

    print("\n=== EXECUTEUR ===")
    state = agent_executeur(state)

    print(f"\n--- RÉSULTAT ---")
    for ex in state["executions"]:
        print(f"Scénario : {ex['scenario_nom']}")
        print(f"Modèle   : {ex['modele']}")
        print(f"Latence  : {ex['latence']:.2f}s")
        print(f"Réponse  : {ex['reponse'][:200]}...")
    if state["erreurs"]:
        print(f"Erreurs  : {state['erreurs']}")