"""
Orchestrateur de l'évaluation NLP (Sprint 4) — remplace l'évaluation heuristique
de src/agents/evaluateur.py par les 4 métriques Ragas réimplémentées dans metrics.py.

⚠️ Coût en temps : ce module fait 4 appels Groq (un par métrique) par exécution
évaluée, en plus de l'appel de génération de la réponse elle-même. Sur un
benchmark de 16 scénarios × 4 modèles = 64 exécutions, ça représente jusqu'à
256 appels Groq supplémentaires. Le rate-limit gratuit de Groq peut être atteint
sur de gros batches — un backoff/retry pourra être ajouté si besoin.
"""

from src.evaluation.metrics import (
    evaluer_faithfulness,
    evaluer_answer_relevancy,
    evaluer_context_precision,
    evaluer_context_recall,
)


def evaluer_execution_ragas(
    reponse: str,
    question: str,
    contexte_chunks: list[str],
    sortie_attendue: str | None = None,
) -> dict:
    """
    Calcule les 4 métriques Ragas pour une exécution (réponse générée par un LLM
    pour un scénario donné), via un LLM-juge (Groq).

    Retourne un dict :
    {
        "faithfulness": {"note": float|None, "justification": str},
        "answer_relevancy": {"note": float|None, "justification": str},
        "context_precision": {"note": float|None, "justification": str},
        "context_recall": {"note": float|None, "justification": str},
        "score_global": float,  # moyenne des notes disponibles (ignore les None)
    }

    Notes entre 0.0 et 1.0 (convention Ragas) — différent de l'échelle 1-5
    utilisée par l'ancienne évaluation heuristique. À garder en tête pour
    l'affichage dans le futur dashboard (Sprint 5).
    """
    resultats = {
        "faithfulness": evaluer_faithfulness(reponse, contexte_chunks),
        "answer_relevancy": evaluer_answer_relevancy(reponse, question),
        "context_precision": evaluer_context_precision(contexte_chunks, question),
        "context_recall": evaluer_context_recall(contexte_chunks, sortie_attendue),
    }

    notes_valides = [
        v["note"] for v in resultats.values() if v["note"] is not None
    ]
    score_global = round(sum(notes_valides) / len(notes_valides), 3) if notes_valides else None

    resultats["score_global"] = score_global
    return resultats


def evaluer_toutes_les_executions(state: dict) -> dict:
    """
    Évalue toutes les exécutions d'un run de benchmark (même rôle que
    agent_evaluateur dans src/agents/evaluateur.py, mais avec les métriques
    Ragas au lieu de l'heuristique).

    Attend un `state` LangGraph contenant "executions" et "scenarios"
    (même format que dans le reste du pipeline).

    Ne fait PAS l'insertion en base ici — retourne juste les résultats, pour
    laisser le choix d'insérer (ou de comparer aux scores heuristiques
    existants) à l'appelant.
    """
    index_scenarios = {s["id"]: s for s in state["scenarios"]}
    evaluations = []

    for execution in state["executions"]:
        scenario = index_scenarios.get(execution["scenario_id"], {})
        chunks_rag = scenario.get("chunks_rag", [])
        sortie_attendue = scenario.get("sortie_attendue")

        print(f"\n  → [Ragas] {execution['scenario_nom']} | {execution['modele']}")

        resultat = evaluer_execution_ragas(
            reponse=execution["reponse"],
            question=scenario.get("prompt", ""),
            contexte_chunks=chunks_rag,
            sortie_attendue=sortie_attendue,
        )

        print(f"     Faithfulness      : {resultat['faithfulness']['note']}")
        print(f"     Answer relevancy  : {resultat['answer_relevancy']['note']}")
        print(f"     Context precision : {resultat['context_precision']['note']}")
        print(f"     Context recall    : {resultat['context_recall']['note']}")
        print(f"     Score global      : {resultat['score_global']}")

        evaluations.append({
            "execution_id": execution["execution_id"],
            "scenario_id": execution["scenario_id"],
            "modele": execution["modele"],
            **resultat,
        })

    return evaluations