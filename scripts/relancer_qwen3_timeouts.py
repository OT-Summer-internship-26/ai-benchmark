"""Relance les scénarios Qwen3 8B (Ollama) qui avaient échoué en timeout.

Ne fait QUE collecteur + exécuteur (pas d'évaluateur), pour séparer le
problème "génération" du problème "juge Ragas" en cours de correction.

Usage :
    python scripts/relancer_qwen3_timeouts.py
"""

from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur

# Scénarios qui avaient timeout lors du premier passage
SCENARIOS_TIMEOUT = [1, 6, 8, 10, 13]

if __name__ == "__main__":
    state_initial = {
        "scenario_ids": SCENARIOS_TIMEOUT,
        "model_names": ["qwen3:8b"],
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    print("=== RELANCE QWEN3 8B — scénarios en timeout ===")
    print(f"Scénarios : {SCENARIOS_TIMEOUT}")
    print(f"Modèle    : qwen3:8b")
    print(f"OLLAMA_TIMEOUT attendu : 180s (vérifie ollama_client.py si ça retimeout)\n")

    print("=== COLLECTEUR ===")
    state = agent_collecteur(state_initial)
    print(f"→ {len(state['scenarios'])} scénarios collectés")

    print("\n=== EXECUTEUR ===")
    state = agent_executeur(state)

    print(f"\n--- RÉSULTAT ---")
    reussis = [ex["scenario_id"] for ex in state["executions"]]
    echoues = [sid for sid in SCENARIOS_TIMEOUT if sid not in reussis]

    for ex in state["executions"]:
        print(f"  ✓ Scénario {ex['scenario_id']} ({ex['scenario_nom']}) — "
              f"execution_id={ex['execution_id']} — {ex['latence']:.2f}s")

    if echoues:
        print(f"\n⚠️  Toujours en échec : {echoues}")
    else:
        print(f"\n✅ Les {len(SCENARIOS_TIMEOUT)} scénarios sont passés.")

    if state["erreurs"]:
        print(f"\nErreurs rencontrées :")
        for err in state["erreurs"]:
            print(f"  - {err}")

    if state["executions"]:
        ids = [ex["execution_id"] for ex in state["executions"]]
        print(f"\n→ Une fois le juge Ragas stabilisé, évalue ces execution_id avec :")
        print(f"   python scripts/re_evaluate_executions.py --ids {','.join(map(str, ids))} --apply")