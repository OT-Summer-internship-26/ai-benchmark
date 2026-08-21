"""Corrige le departement des scénarios mal catégorisés :
  - 'Agents IA et Automatisation' (16 scénarios, seed_scenarios_complement.py)
  - 'Conseiller Service Client'   (2 scénarios, seed_scenarios.py)
vers le vrai nom de département officiel : 'Service Client'
(cf. document de référence des besoins IA par département).

Usage :
  python scripts/corriger_departement_service_client.py --dry-run
  python scripts/corriger_departement_service_client.py --apply
"""
import argparse
from sqlalchemy import text
from src.database.connection import engine

ANCIENS_NOMS = ("Agents IA et Automatisation", "Conseiller Service Client")
NOUVEAU_NOM = "Service Client"


def main(dry_run: bool):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, departement, nom_cas_usage
                FROM scenarios
                WHERE departement IN :anciens
                ORDER BY departement, nom_cas_usage
            """),
            {"anciens": ANCIENS_NOMS},
        ).fetchall()

        print(f"{len(rows)} scénarios seront reclassés vers '{NOUVEAU_NOM}' :\n")
        for sid, dep, nom in rows:
            print(f"  [{sid}] {dep!r} -> {NOUVEAU_NOM!r} | {nom}")

        if dry_run:
            print("\n(dry-run) Aucune modification appliquée. Relance avec --apply pour confirmer.")
            return

        result = conn.execute(
            text("""
                UPDATE scenarios
                SET departement = :nouveau
                WHERE departement IN :anciens
            """),
            {"nouveau": NOUVEAU_NOM, "anciens": ANCIENS_NOMS},
        )
        conn.commit()
        print(f"\n✅ {result.rowcount} scénarios mis à jour vers '{NOUVEAU_NOM}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Applique réellement la correction")
    args = parser.parse_args()
    main(dry_run=not args.apply)