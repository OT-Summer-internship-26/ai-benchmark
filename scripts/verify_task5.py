"""
Verification script for Task 5:
- Verify no duplicate (execution_id, critere)
- Verify no methode IS NULL
- Test dashboard queries to ensure numeric values where computable
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text, create_engine
from src.config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL)

def run_verification():
    with engine.connect() as conn:
        print("=" * 80)
        print("TASK 5 VERIFICATION CHECKS")
        print("=" * 80)

        # 1. Duplicates check
        dups = conn.execute(text("""
            SELECT execution_id, critere, COUNT(*)
            FROM scores
            WHERE methode = 'ragas' AND COALESCE(is_legacy, FALSE) = FALSE
            GROUP BY execution_id, critere
            HAVING COUNT(*) > 1
        """)).fetchall()
        print(f"1. Duplicate (execution_id, critere) rows: {len(dups)}")
        if dups:
            for d in dups:
                print(f"   ERROR DUPLICATE: {d}")
        else:
            print("   -> OK: Zero duplicate pairs found.")

        # 2. methode NULL check
        null_methode = conn.execute(text("""
            SELECT COUNT(*)
            FROM scores
            WHERE methode IS NULL
        """)).scalar()
        print(f"\n2. Scores with methode IS NULL: {null_methode}")
        if null_methode == 0:
            print("   -> OK: Zero rows with methode IS NULL.")
        else:
            print(f"   WARNING: {null_methode} rows have NULL methode.")

        # 3. Overall scores count & status
        total_scores = conn.execute(text("SELECT COUNT(*) FROM scores")).scalar()
        ragas_modern = conn.execute(text("SELECT COUNT(*) FROM scores WHERE methode = 'ragas' AND COALESCE(is_legacy, FALSE) = FALSE")).scalar()
        ragas_legacy = conn.execute(text("SELECT COUNT(*) FROM scores WHERE COALESCE(is_legacy, FALSE) = TRUE")).scalar()
        print(f"\n3. Total scores in DB: {total_scores} (modern ragas: {ragas_modern}, legacy: {ragas_legacy})")

        # 4. Modern RAGAS metrics distribution
        metrics_dist = conn.execute(text("""
            SELECT critere, COUNT(*), MIN(note), AVG(note), MAX(note),
                   COUNT(*) FILTER (WHERE note = 0.0) as count_zero,
                   COUNT(*) FILTER (WHERE note IS NULL) as count_null
            FROM scores
            WHERE methode = 'ragas' AND COALESCE(is_legacy, FALSE) = FALSE
            GROUP BY critere
            ORDER BY critere
        """)).fetchall()
        print("\n4. Modern RAGAS metrics distribution:")
        print(f"   {'Critere':<20} | {'Total':>5} | {'Min':>5} | {'Avg':>5} | {'Max':>5} | {'Zeros':>5} | {'Nulls':>5}")
        print("   " + "-"*65)
        for r in metrics_dist:
            print(f"   {r[0]:<20} | {r[1]:>5} | {r[2]:>5.3f} | {r[3]:>5.3f} | {r[4]:>5.3f} | {r[5]:>5} | {r[6]:>5}")

        # 5. Dashboard query simulation
        print("\n5. Dashboard query simulation (overview per model):")
        dashboard_summary = conn.execute(text("""
            SELECT 
                m.nom as model_name,
                COUNT(DISTINCT e.id) as exec_count,
                ROUND(AVG(CASE WHEN sc.critere = 'faithfulness' THEN sc.note END)::numeric, 3) as avg_faithfulness,
                ROUND(AVG(CASE WHEN sc.critere = 'answer_relevancy' THEN sc.note END)::numeric, 3) as avg_relevancy,
                ROUND(AVG(CASE WHEN sc.critere = 'context_precision' THEN sc.note END)::numeric, 3) as avg_precision,
                ROUND(AVG(CASE WHEN sc.critere = 'context_recall' THEN sc.note END)::numeric, 3) as avg_recall,
                ROUND(AVG(CASE WHEN sc.critere = 'score_global' THEN sc.note END)::numeric, 3) as avg_global
            FROM executions e
            JOIN modeles m ON e.modele_id = m.id
            LEFT JOIN scores sc ON sc.execution_id = e.id
                AND sc.methode = 'ragas'
                AND COALESCE(sc.is_legacy, FALSE) = FALSE
            GROUP BY m.nom
            ORDER BY avg_global DESC NULLS LAST
        """)).fetchall()
        print(f"   {'Model':<25} | {'Execs':>5} | {'Faith':>6} | {'Relev':>6} | {'Prec':>6} | {'Recall':>6} | {'Global':>6}")
        print("   " + "-"*75)
        for row in dashboard_summary:
            print(f"   {row[0]:<25} | {row[1]:>5} | {str(row[2]):>6} | {str(row[3]):>6} | {str(row[4]):>6} | {str(row[5]):>6} | {str(row[6]):>6}")

if __name__ == "__main__":
    run_verification()
