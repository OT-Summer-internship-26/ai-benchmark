"""Re-evaluate specific execution IDs using the RAGAS evaluator.

Usage:
  .venv\Scripts\python.exe scripts/re_evaluate_executions.py --ids 15,16

This script will insert RAGAS metric rows into `scores` for the given
execution IDs. It skips metrics whose note is None.
"""
import argparse
import sys
from sqlalchemy import text

sys.path.insert(0, r'c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark')
from src.database.connection import engine
from src.evaluation.deepeval_runner import evaluer_execution_ragas
from src.rag.vector_store import search_similar


def fetch_execution(conn, exec_id: int):
    q = text("""
        SELECT e.id, e.scenario_id, e.reponse_generee as reponse, e.modele_id,
               m.nom as modele_nom
        FROM executions e JOIN modeles m ON m.id=e.modele_id
        WHERE e.id = :eid
    """)
    return conn.execute(q, {"eid": exec_id}).mappings().first()


def fetch_scenario(conn, scenario_id: int):
    q = text("""
        SELECT id, nom_cas_usage, prompt, sortie_attendue, departement
        FROM scenarios WHERE id = :sid
    """)
    row = conn.execute(q, {"sid": scenario_id}).mappings().first()
    if not row:
        return None
    scenario = dict(row)
    # Recompute chunks via vector store (same logic as agent_collecteur)
    try:
        chunks = search_similar(query=scenario.get("prompt", ""), departement=scenario.get("departement", ""), top_k=8)
    except Exception:
        chunks = []
    scenario["chunks_rag"] = chunks
    return scenario


def insert_scores(conn, execution_id: int, resultat: dict):
    criteres_a_inserer = {
        "faithfulness": resultat["faithfulness"],
        "answer_relevancy": resultat["answer_relevancy"],
        "context_precision": resultat["context_precision"],
        "context_recall": resultat["context_recall"],
    }

    nb_inseres = 0
    for critere, detail in criteres_a_inserer.items():
        if detail.get("note") is None:
            continue
        conn.execute(
            text("""
                INSERT INTO scores (execution_id, critere, note, commentaire)
                VALUES (:exec_id, :critere, :note, :commentaire)
            """),
            {
                "exec_id": execution_id,
                "critere": critere,
                "note": float(detail["note"]),
                "commentaire": detail.get("justification", "")[:500],
            },
        )
        nb_inseres += 1

    if resultat.get("score_global") is not None:
        conn.execute(
            text("""
                INSERT INTO scores (execution_id, critere, note, commentaire)
                VALUES (:exec_id, :critere, :note, :commentaire)
            """),
            {
                "exec_id": execution_id,
                "critere": "score_global",
                "note": float(resultat["score_global"]),
                "commentaire": "Re-eval RAGAS",
            },
        )
        nb_inseres += 1

    return nb_inseres


def main(ids: list[int], dry_run: bool = True):
    with engine.connect() as conn:
        for eid in ids:
            exec_row = fetch_execution(conn, eid)
            if not exec_row:
                print(f"Execution {eid} not found, skipping")
                continue

            scenario = fetch_scenario(conn, exec_row["scenario_id"])
            if not scenario:
                print(f"Scenario {exec_row['scenario_id']} not found for exec {eid}, skipping")
                continue

            print(f"Re-evaluating execution {eid} (model={exec_row['modele_nom']})")

            resultat = evaluer_execution_ragas(
                reponse=exec_row["reponse"],
                question=scenario.get("prompt", ""),
                contexte_chunks=scenario.get("chunks_rag", []),
                sortie_attendue=scenario.get("sortie_attendue"),
            )

            print("  => score_global:", resultat.get("score_global"))

            if dry_run:
                print("  (dry-run) would insert metrics where note is not None")
            else:
                try:
                    nb = insert_scores(conn, eid, resultat)
                    conn.commit()
                    print(f"  ✓ inserted {nb} score rows for execution {eid}")
                except Exception as e:
                    print(f"  ✗ error inserting scores for {eid}: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="Comma-separated execution IDs")
    parser.add_argument("--apply", action="store_true", help="Actually insert rows (default is dry-run)")
    args = parser.parse_args()
    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    main(ids, dry_run=not args.apply)
