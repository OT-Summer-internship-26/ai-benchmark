from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur
from src.agents.evaluateur import agent_evaluateur
from src.agents.consolidateur import agent_consolidateur

if __name__ == "__main__":
    state_initial = {
        "scenario_ids": [1, 11],           # RH + NOC
        "model_names": ["llama3.1:8b", "mistral:7b"],  # 2 modèles
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    print("DÉMARRAGE DU PIPELINE BENCHMARK")
    print(f"Scénarios : {state_initial['scenario_ids']}")
    print(f"Modèles   : {state_initial['model_names']}")
    print(f"Total     : {len(state_initial['scenario_ids']) * len(state_initial['model_names'])} exécutions\n")

    state = agent_collecteur(state_initial)
    state = agent_executeur(state)
    state = agent_evaluateur(state)
    state = agent_consolidateur(state)

    if state["erreurs"]:
        print(f"\nErreurs rencontrées : {state['erreurs']}")