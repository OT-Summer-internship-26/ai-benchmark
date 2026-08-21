"""Supprime les scénarios doublons dans 'Service Client' (id 83, 84),
qui sont des copies exactes de id 15 et 16 sans aucune exécution
associée. Les originaux (15, 16, avec exécutions) sont conservés.

Usage :
    python scripts/supprimer_doublons_service_client.py --dry-run
    python scripts/supprimer_doublons_service_client.py --apply
"""
import argparse
from sqlalchemy import text
from src.database.connection import engine

IDS_A_SUPPRIMER = (83, 84)


def main(dry_run: bool):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, departement, nom_cas_usage,
                       (SELECT COUNT(*) FROM executions e WHERE e.scenario_id = scenarios.id) as nb_exec
                FROM scenarios
                WHERE id IN :ids
                ORDER BY id
            """),
            {"ids": IDS_A_SUPPRIMER},
        ).fetchall()

        print("Scénarios ciblés pour suppression :")
        for sid, dep, nom, nb_exec in rows:
            print(f"  [{sid}] {dep} | {nom} — {nb_exec} exécution(s)")

        # Sécurité : on refuse de supprimer si l'un d'eux a des exécutions
        avec_executions = [r for r in rows if r[3] > 0]
        if avec_executions:
            print("\n❌ ARRÊT : au moins un des scénarios ciblés a des exécutions. "
                  "Vérifie les ids avant de continuer, rien n'a été supprimé.")
            return

        if dry_run:
            print("\n(dry-run) Aucune suppression effectuée. Relance avec --apply pour confirmer.")
            return

        result = conn.execute(
            text("DELETE FROM scenarios WHERE id IN :ids"),
            {"ids": IDS_A_SUPPRIMER},
        )
        conn.commit()
        print(f"\n✅ {result.rowcount} scénarios supprimés.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Applique réellement la suppression")
    args = parser.parse_args()
    main(dry_run=not args.apply)