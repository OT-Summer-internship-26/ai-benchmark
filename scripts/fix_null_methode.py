"""
Fix scores rows with methode = NULL.

These are historical rows inserted before the 'methode' column was added.
They should be tagged as 'ragas' if they match RAGAS metric criteria
(score between 0 and 1, and critere is a known RAGAS metric).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL


def main():
    dry_run = "--dry-run" in sys.argv
    engine = create_engine(DATABASE_URL)

    ragas_criteria = (
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "score_global",
    )

    with engine.connect() as conn:
        # 1. Diagnostic: show current NULL methode rows
        diag = conn.execute(text("""
            SELECT critere, COUNT(*) as cnt, 
                   MIN(note) as min_note, MAX(note) as max_note
            FROM scores 
            WHERE methode IS NULL
            GROUP BY critere
            ORDER BY critere
        """)).fetchall()

        print("=" * 60)
        print("DIAGNOSTIC — Scores with methode = NULL")
        print("=" * 60)
        if not diag:
            print("✅ No rows with methode = NULL. Nothing to fix.")
            return

        total = 0
        for row in diag:
            critere, cnt, min_note, max_note = row
            print(f"  {critere:<25} {cnt:>4} rows  (notes: {min_note:.3f} – {max_note:.3f})")
            total += cnt
        print(f"  {'TOTAL':<25} {total:>4} rows")

        # 2. Count fixable rows (RAGAS criteria with valid score range)
        fixable = conn.execute(text("""
            SELECT COUNT(*) FROM scores
            WHERE methode IS NULL
              AND critere IN :criteria
              AND note BETWEEN 0 AND 1
        """).bindparams(
            criteria=ragas_criteria
        )).scalar()

        mode_label = "[DRY-RUN]" if dry_run else "[FIX]"
        print(f"\n{mode_label}: {fixable} rows match RAGAS criteria and will be updated.")

        if dry_run:
            print("\n-> Run without --dry-run to apply the fix.")
            return

        # 3. Apply the fix
        result = conn.execute(text("""
            UPDATE scores
            SET methode = 'ragas', is_legacy = FALSE
            WHERE methode IS NULL
              AND critere IN :criteria
              AND note BETWEEN 0 AND 1
        """).bindparams(
            criteria=ragas_criteria
        ))
        conn.commit()

        print(f"\n[OK] Updated {result.rowcount} rows: methode='ragas', is_legacy=FALSE")

        # 4. Verify
        remaining = conn.execute(text("""
            SELECT COUNT(*) FROM scores WHERE methode IS NULL
        """)).scalar()
        print(f"   Remaining NULL methode rows: {remaining}")


if __name__ == "__main__":
    main()
