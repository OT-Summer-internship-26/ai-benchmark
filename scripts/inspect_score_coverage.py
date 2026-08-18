"""
Pour chaque execution du departement donne, montre quels criteres Ragas
sont presents/manquants -- pour comprendre pourquoi une execution ne compte
pas comme "totalement notee".

Usage:
  .venv\\Scripts\\python.exe scripts\\inspect_score_coverage.py "IT & Architecture"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from src.database.connection import engine

REQUIRED = {"faithfulness", "answer_relevancy", "context_precision", "context_recall"}


def run(department: str):
    with engine.connect() as conn:
        executions = conn.execute(text("""
            SELECT e.id, m.nom, s.nom_cas_usage
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            JOIN modeles m ON m.id = e.modele_id
            WHERE s.departement = :dep
            ORDER BY e.id
        """), {"dep": department}).fetchall()

        if not executions:
            print(f"Aucune execution pour '{department}'.")
            return

        for exec_id, modele, scenario in executions:
            scores = conn.execute(text("""
                SELECT critere, note, methode
                FROM scores
                WHERE execution_id = :eid
            """), {"eid": exec_id}).fetchall()

            present = {critere for critere, note, methode in scores if note is not None}
            missing = REQUIRED - present
            out_of_range = [
                (critere, note) for critere, note, methode in scores
                if critere in REQUIRED and note is not None and not (0 <= note <= 1)
            ]

            print(f"Execution {exec_id} | modele={modele} | scenario={scenario}")
            print(f"  Criteres presents avec note non-null: {present or '(aucun)'}")
            print(f"  Criteres Ragas manquants: {missing or '(aucun, complet!)'}")
            if out_of_range:
                print(f"  ATTENTION notes hors [0,1]: {out_of_range}")
            print(f"  Toutes les lignes scores brutes: {scores}")
            print()


if __name__ == "__main__":
    dept = sys.argv[1] if len(sys.argv) > 1 else "IT & Architecture"
    run(dept)