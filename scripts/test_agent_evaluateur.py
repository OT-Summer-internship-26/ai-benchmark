from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur
from src.agents.evaluateur import agent_evaluateur

if __name__ == "__main__":
    state_initial = {
        "scenario_ids": [1],
        "model_names": ["llama3.1:8b"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    state = agent_collecteur(state_initial)
    state = agent_executeur(state)
    state = agent_evaluateur(state)

    print(f"\n--- SCORES FINAUX ---")
    for item in state["scores"]:
        print(f"\nScénario : {item['scenario_nom']} | Modèle : {item['modele']}")
        for critere, note in item["scores"].items():
            print(f"  {critere} : {note}/5")
    if state["erreurs"]:
        print(f"\nErreurs : {state['erreurs']}")