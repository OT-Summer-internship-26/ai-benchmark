"""
Script de diagnostic : affiche côte à côte la réponse générée, le contexte RAG
(recalculé, car non sauvegardé en base) et le jugement de faithfulness, pour un
execution_id donné. Permet de vérifier à l'œil si un score bas est un vrai
signal (hallucination réelle) ou un problème de calibration du juge.

Usage :
    python -m scripts.diagnostic_faithfulness <execution_id>

Exemple :
    python -m scripts.diagnostic_faithfulness 39
"""

import sys
from sqlalchemy import text
from src.database.connection import engine
from src.rag.vector_store import search_similar
from src.evaluation.metrics import evaluer_faithfulness, evaluer_context_precision


def diagnostiquer(execution_id: int):
    with engine.connect() as conn:
        execution = conn.execute(
            text("""
                SELECT e.id, e.scenario_id, e.reponse_generee, m.nom AS modele_nom
                FROM executions e
                JOIN modeles m ON m.id = e.modele_id
                WHERE e.id = :id
            """),
            {"id": execution_id}
        ).mappings().fetchone()

        if not execution:
            print(f"Aucune exécution trouvée avec l'id {execution_id}.")
            return

        scenario = conn.execute(
            text("SELECT * FROM scenarios WHERE id = :id"),
            {"id": execution["scenario_id"]}
        ).mappings().fetchone()

    print("=" * 70)
    print(f"DIAGNOSTIC — execution_id={execution_id} | modèle={execution['modele_nom']}")
    print(f"Scénario : [{scenario['id']}] {scenario['nom_cas_usage']} ({scenario['departement']})")
    print("=" * 70)

    print("\n--- QUESTION / PROMPT DU SCÉNARIO ---")
    print(scenario["prompt"])

    print("\n--- RÉPONSE GÉNÉRÉE (sauvegardée en base) ---")
    print(execution["reponse_generee"])

    print("\n--- RECALCUL DU CONTEXTE RAG (search_similar, top_k=8) ---")
    print("⚠️  Ce contexte est recalculé maintenant, pas garanti identique à 100%")
    print("    à celui utilisé au moment de la génération (dépend de l'état de la base).")
    chunks = search_similar(
        query=scenario["prompt"],
        departement=scenario["departement"],
        top_k=8
    )
    for i, chunk in enumerate(chunks, 1):
        print(f"\n[Chunk {i}]")
        print(chunk[:500] + ("..." if len(chunk) > 500 else ""))

    print("\n--- RE-JUGEMENT EN DIRECT (avec justification complète) ---")
    resultat_faithfulness = evaluer_faithfulness(execution["reponse_generee"], chunks)
    print(f"Faithfulness : {resultat_faithfulness['note']}")
    print(f"Justification : {resultat_faithfulness['justification']}")

    resultat_precision = evaluer_context_precision(chunks, scenario["prompt"])
    print(f"\nContext precision : {resultat_precision['note']}")
    print(f"Justification : {resultat_precision['justification']}")

    print("\n" + "=" * 70)
    print("À toi de juger maintenant : en lisant la réponse et les chunks")
    print("ci-dessus, est-ce que la réponse te semble vraiment s'appuyer sur")
    print("le contexte, ou invente-t-elle des choses qui n'y sont pas ?")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python -m scripts.diagnostic_faithfulness <execution_id>")
        sys.exit(1)

    diagnostiquer(int(sys.argv[1]))