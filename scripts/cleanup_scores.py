#!/usr/bin/env python3
"""
Script safe de nettoyage des anciens scores heuristiques.

Usage:
  python scripts/cleanup_scores.py --dry-run
  python scripts/cleanup_scores.py --apply --remove-orphan-executions

Il supprime par défaut les critères heuristiques historiques
('completude','structure','fidelite_rag','honnetete') et les entrées
`score_global` dont la note > 1.0 (ancienne échelle).
"""
import argparse
from sqlalchemy import text
from src.database.connection import engine


def main(dry_run: bool, remove_orphans: bool):
    # Distinction based on critere names
    raga_criteria = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    legacy_criteria = ("completude", "structure", "fidelite_rag", "honnetete")

    with engine.connect() as conn:
        # Counts: total rows matching legacy markers (by critere name or score_global > 1.0)
        q_count = text(
            "SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)"
        )
        total = conn.execute(q_count).scalar()
        print(f"Found {total} legacy-identified score rows (by critere name or score_global>1.0).")

        # Breakdown: how many rows would be tagged heuristique vs ragas vs unknown
        q_heur = text(
            "SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)"
        )
        q_ragas = text(
            "SELECT COUNT(*) FROM scores WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') OR (critere='score_global' AND note <= 1.0)"
        )
        heur_count = conn.execute(q_heur).scalar()
        ragas_count = conn.execute(q_ragas).scalar()
        q_unknown = text("SELECT COUNT(*) FROM scores WHERE critere NOT IN ('completude','structure','fidelite_rag','honnetete','faithfulness','answer_relevancy','context_precision','context_recall','score_global')")
        unknown_count = conn.execute(q_unknown).scalar()

        print(f"Would tag {heur_count} rows as 'heuristique'.")
        print(f"Would tag {ragas_count} rows as 'ragas'.")
        print(f"{unknown_count} rows would remain 'unknown' (other critere names).")

        # Show example execution_ids that contain legacy criteria (for inspection)
        q_execs_with_legacy = text(
            "SELECT DISTINCT execution_id FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0) LIMIT 100"
        )
        execs_legacy = [r[0] for r in conn.execute(q_execs_with_legacy).fetchall()]
        print(f"Example execution_ids with legacy criteria (up to 100): {execs_legacy}")

        # Prepare SQL statements that would be run in apply mode
        alter_sql = "ALTER TABLE scores ADD COLUMN IF NOT EXISTS methode TEXT"
        update_heur_sql = (
            "UPDATE scores SET methode = 'heuristique' WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)"
        )
        update_ragas_sql = (
            "UPDATE scores SET methode = 'ragas' WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') OR (critere='score_global' AND note <= 1.0)"
        )
        update_unknown_sql = "UPDATE scores SET methode = 'unknown' WHERE methode IS NULL"

        print('\nSQL to run on --apply:')
        print(alter_sql)
        print(update_heur_sql)
        print(update_ragas_sql)
        print(update_unknown_sql)

        if dry_run:
            print('\nDry run complete: no schema or data changes applied.')
        else:
            print('\nApplying tags to scores table...')
            conn.execute(text(alter_sql))
            res1 = conn.execute(text(update_heur_sql))
            res2 = conn.execute(text(update_ragas_sql))
            res3 = conn.execute(text(update_unknown_sql))
            conn.commit()
            print(f"Applied tags: heuristique updated rows: {res1.rowcount}, ragas updated rows: {res2.rowcount}, unknown updated rows: {res3.rowcount}")

        # Orphan executions reporting (no deletions performed here)
        if remove_orphans:
            q_orphans = text(
                "SELECT e.id, m.nom as modele, e.scenario_id, e.date_execution FROM executions e JOIN modeles m ON m.id=e.modele_id LEFT JOIN scores s ON s.execution_id = e.id WHERE s.id IS NULL ORDER BY e.date_execution DESC"
            )
            orphan_rows = [dict(r) for r in conn.execute(q_orphans).mappings().all()]
            print(f"Found {len(orphan_rows)} orphan executions (no scores).")
            if orphan_rows:
                print('Listing orphan executions (id, modele, scenario_id, date_execution):')
                for r in orphan_rows:
                    print(r)
                if not dry_run:
                    print('Note: --apply does not delete orphan executions in this updated workflow. To remove them, run a dedicated delete with explicit confirmation.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Ne pas supprimer, afficher seulement")
    parser.add_argument("--apply", action="store_true", help="Appliquer les suppressions")
    parser.add_argument("--remove-orphan-executions", action="store_true", help="Supprimer les exécutions sans scores")
    args = parser.parse_args()

    dry_run = not args.apply
    main(dry_run=dry_run, remove_orphans=args.remove_orphan_executions)
