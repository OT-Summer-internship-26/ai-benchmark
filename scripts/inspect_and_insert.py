"""Inspecte le résultat RAGAS pour des execution IDs, affiche les détails
et insère uniquement les critères manquants (évite les doublons).

Usage:
  .venv\Scripts\python.exe scripts/inspect_and_insert.py --ids 12,8,15,7
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
    try:
        chunks = search_similar(query=scenario.get("prompt", ""), departement=scenario.get("departement", ""), top_k=8)
    except Exception:
        chunks = []
    scenario["chunks_rag"] = chunks
    return scenario


def existing_criteria(conn, exec_id: int):
    q = text("SELECT critere FROM scores WHERE execution_id = :eid")
    return {r[0] for r in conn.execute(q, {"eid": exec_id}).fetchall()}


def insert_missing(conn, exec_id: int, resultat: dict, existing: set):
    criteres = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "score_global"]
    inserted = 0
    for crit in criteres:
        if crit in existing:
            continue
        val = None
        comment = None
        if crit == "score_global":
            val = resultat.get("score_global")
            comment = "Re-eval RAGAS (safe insert)"
        else:
            detail = resultat.get(crit, {})
            val = detail.get("note")
            comment = detail.get("justification", "")[:500]

        if val is None:
            continue

        conn.execute(
            text("""
                INSERT INTO scores (execution_id, critere, note, commentaire)
                VALUES (:exec_id, :critere, :note, :commentaire)
            """),
            {"exec_id": exec_id, "critere": crit, "note": float(val), "commentaire": comment},
        )
        inserted += 1

    return inserted


def main(ids: list[int]):
    with engine.connect() as conn:
        for eid in ids:
            print(f"\n--- Execution {eid} ---")
            exec_row = fetch_execution(conn, eid)
            if not exec_row:
                print("Not found")
                continue
            scenario = fetch_scenario(conn, exec_row["scenario_id"]) or {}

            print(f"Model: {exec_row['modele_nom']}, scenario_id: {exec_row['scenario_id']}")

            try:
                resultat = evaluer_execution_ragas(
                    reponse=exec_row["reponse"],
                    question=scenario.get("prompt", ""),
                    contexte_chunks=scenario.get("chunks_rag", []),
                    sortie_attendue=scenario.get("sortie_attendue"),
                )
            except Exception as e:
                print(f"Error during eval: {e}")
                continue

            print("Resultat detail:")
            for k, v in resultat.items():
                print(f"  {k}: {v}")

            exist = existing_criteria(conn, eid)
            print("Existing criteria in DB:", exist)

            inserted = insert_missing(conn, eid, resultat, exist)
            if inserted:
                conn.commit()
            print(f"Inserted {inserted} new score rows for execution {eid}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="Comma-separated execution IDs")
    args = parser.parse_args()
    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    main(ids)
