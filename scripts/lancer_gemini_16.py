"""Lance les 16 scénarios avec Gemini 3.1 Flash-Lite (API Google).

Ne fait QUE collecteur + exécuteur (pas d'évaluateur), pour séparer le
problème "génération" du problème "juge Ragas" en cours de correction.

Usage :
    python scripts/lancer_gemini_16.py
"""

from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur

# Tous les scénarios du catalogue (RH:5 + Marketing:2 + IT:3 + NOC:1 +
# Productivité:3 + Agents IA:2 = 16), ids attribués séquentiellement par seed_scenarios.py
TOUS_LES_SCENARIOS = list(range(1, 17))

if __name__ == "__main__":
    state_initial = {
        "scenario_ids": TOUS_LES_SCENARIOS,
        "model_names": ["gemini-3.1-flash-lite"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    print("=== BENCHMARK GEMINI 3.1 FLASH-LITE — 16 scénarios ===")
    print(f"Scénarios : {TOUS_LES_SCENARIOS}")
    print(f"Modèle    : gemini-3.1-flash-lite (API Google, free tier)\n")

    print("=== COLLECTEUR ===")
    state = agent_collecteur(state_initial)
    print(f"-> {len(state['scenarios'])} scénarios collectés")

    print("\n=== EXECUTEUR ===")
    state = agent_executeur(state)

    print(f"\n--- RÉSULTAT ---")
    reussis = [ex["scenario_id"] for ex in state["executions"]]
    echoues = [sid for sid in TOUS_LES_SCENARIOS if sid not in reussis]

    for ex in state["executions"]:
        print(f"  OK Scénario {ex['scenario_id']} ({ex['scenario_nom']}) — "
              f"execution_id={ex['execution_id']} — {ex['latence']:.2f}s")

    if echoues:
        print(f"\nEn échec : {echoues}")
    else:
        print(f"\nLes {len(TOUS_LES_SCENARIOS)} scénarios sont passés.")

    if state["erreurs"]:
        print(f"\nErreurs rencontrées :")
        for err in state["erreurs"]:
            print(f"  - {err}")

    if state["executions"]:
        ids = [ex["execution_id"] for ex in state["executions"]]
        print(f"\n-> Une fois le juge Ragas stabilisé, évalue ces execution_id avec :")
        print(f"   python scripts/re_evaluate_executions.py --ids {','.join(map(str, ids))} --apply")