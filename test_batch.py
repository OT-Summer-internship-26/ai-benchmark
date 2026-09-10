from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur
from src.agents.evaluateur import agent_evaluateur
from src.agents.consolidateur import agent_consolidateur
from src.observability.langfuse_client import flush_langfuse

# 1. ÉTAT INITIAL
state_initial = {
    "scenario_ids": [1, 2, 8],
    "model_names": ["llama3.1:8b", "mistral:7b","gemma2:9b",
        "qwen2.5:7b",
        "qwen3:8b",
        "gemini-3.1-flash-lite"],
    "scenarios": [],
    "executions": [],
    "scores": [],
    "rapport": None,
    "erreurs": [],
}

print("=======================================================")
print("🚀 EXECUTION DU PIPELINE BENCHMARK MULTI-AGENTS")
print("=======================================================\n")

# 2. COLLECTEUR
state = agent_collecteur(state_initial)
print(f"[1/4] Collecteur : {len(state['scenarios'])} scénarios collectés")

# 3. EXECUTEUR
state = agent_executeur(state)
print(f"[2/4] Exécuteur : {len(state['executions'])} exécutions terminées")

# Affichage rapide des tokens / coûts issus de l'exécuteur
for ex in state["executions"]:
    tokens = ex.get("tokens_utilises", "N/A")
    cout = ex.get("cout_estime", 0)
    print(f"    • {ex['scenario_nom']} | {ex['modele']} | {tokens} tokens | ${cout:.6f}")

# 4. EVALUATEUR (Calcul des métriques Ragas & Sauvegarde BDD)
print("\n[3/4] Évaluateur : Lancement de l'évaluation Ragas...")
state = agent_evaluateur(state)

# 5. CONSOLIDATEUR (Synthèse & Classement des modèles)
print("\n[4/4] Consolidateur : Génération du rapport comparatif...")
state = agent_consolidateur(state)

# Flush vers Langfuse (Traces)
flush_langfuse()

# 6. GESTION DES ERREURS D'EXÉCUTION
if state["erreurs"]:
    print("\n--- AVERTISSEMENTS / ERREURS ---")
    for e in state["erreurs"]:
        print("⚠️ ERREUR:", e)

print("\n=======================================================")
print("✅ BENCHMARK TERMINÉ")
print("=======================================================")