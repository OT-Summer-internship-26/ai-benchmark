"""
Diagnostic: for each department, show
  - raw execution count (scenarios x executions, no score filter)
  - how many score rows have methode='ragas' vs methode IS NULL
    (this is what proves/disproves the bug)
  - how many (execution, modele) pairs pass the OLD (buggy) valid_executions
    filter vs the NEW (fixed) filter
  - how many models clear the min_scored_executions threshold under each

Usage:
  .venv\\Scripts\\python.exe scripts/diagnose_client_recommendation.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from src.database.connection import engine

DEPARTMENTS = [
    "RH & Communication",
    "Marketing & Digital",
    "IT & Architecture",
    "Réseau / Support Technique (NOC)",
    "Productivité Personnelle",
    "Agents IA et Automatisation",  # "Conseiller Service Client" is the métier, this is the départment
]

MIN_SCORED_EXECUTIONS = 2

OLD_FILTER_SQL = """
    SELECT e.id, e.modele_id
    FROM scenarios s
    JOIN executions e ON e.scenario_id = s.id
    JOIN scores sc ON sc.execution_id = e.id
    WHERE s.departement = :dep
      AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
      AND sc.methode = 'ragas'
      AND sc.note BETWEEN 0 AND 1
    GROUP BY e.id, e.modele_id
    HAVING COUNT(DISTINCT sc.critere) = 4
"""

NEW_FILTER_SQL = """
    SELECT e.id, e.modele_id
    FROM scenarios s
    JOIN executions e ON e.scenario_id = s.id
    JOIN scores sc ON sc.execution_id = e.id
    WHERE s.departement = :dep
      AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
      AND sc.note BETWEEN 0 AND 1
    GROUP BY e.id, e.modele_id
    HAVING COUNT(DISTINCT sc.critere) = 4
"""

MODELS_PASSING_SQL_TEMPLATE = """
    SELECT modele_id, COUNT(*) as n
    FROM ({inner}) t
    GROUP BY modele_id
    HAVING COUNT(*) >= :min_n
"""


def run():
    with engine.connect() as conn:
        # Sanity check: does 'methode' column even have non-null values anywhere?
        try:
            methode_counts = conn.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE methode = 'ragas') AS methode_ragas,
                    COUNT(*) FILTER (WHERE methode IS NULL) AS methode_null,
                    COUNT(*) AS total
                FROM scores
            """)).fetchone()
            print(f"Global scores table: methode='ragas' -> {methode_counts[0]}, "
                  f"methode IS NULL -> {methode_counts[1]}, total rows -> {methode_counts[2]}")
        except Exception as e:
            print(f"Could not inspect 'methode' column (may not exist): {e}")
        print()

        for dep in DEPARTMENTS:
            print("=" * 80)
            print(f"DEPARTMENT: {dep}")

            raw_exec = conn.execute(text("""
                SELECT COUNT(e.id)
                FROM scenarios s
                LEFT JOIN executions e ON e.scenario_id = s.id
                WHERE s.departement = :dep
            """), {"dep": dep}).scalar() or 0
            print(f"  Raw execution count (no score filter): {raw_exec}")

            old_rows = conn.execute(text(OLD_FILTER_SQL), {"dep": dep}).fetchall()
            new_rows = conn.execute(text(NEW_FILTER_SQL), {"dep": dep}).fetchall()
            print(f"  Fully-scored (exec, model) pairs — OLD filter (methode='ragas'): {len(old_rows)}")
            print(f"  Fully-scored (exec, model) pairs — NEW filter (no methode dependency): {len(new_rows)}")

            old_models = conn.execute(
                text(MODELS_PASSING_SQL_TEMPLATE.format(inner=OLD_FILTER_SQL)),
                {"dep": dep, "min_n": MIN_SCORED_EXECUTIONS},
            ).fetchall()
            new_models = conn.execute(
                text(MODELS_PASSING_SQL_TEMPLATE.format(inner=NEW_FILTER_SQL)),
                {"dep": dep, "min_n": MIN_SCORED_EXECUTIONS},
            ).fetchall()

            print(f"  Models clearing min_scored_executions={MIN_SCORED_EXECUTIONS} — OLD: {len(old_models)} "
                  f"{[(m, n) for m, n in old_models]}")
            print(f"  Models clearing min_scored_executions={MIN_SCORED_EXECUTIONS} — NEW: {len(new_models)} "
                  f"{[(m, n) for m, n in new_models]}")

            if not old_models and new_models:
                print("  => CONFIRMS BUG: old filter blocks this department, new filter does not.")
            elif not new_models:
                print("  => Genuinely insufficient data even after the fix (not a bug).")
            else:
                print("  => Both filters pass — old filter wasn't the blocker here.")
            print()


if __name__ == "__main__":
    run()