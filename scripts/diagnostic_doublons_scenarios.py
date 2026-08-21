"""Diagnostic des écarts par rapport à la cible de 16 scénarios/département.

1. Détecte les doublons exacts (même departement + nom_cas_usage).
2. Liste en détail les scénarios de RH & Communication, Réseau/NOC et
   Service Client pour décider quoi supprimer/ajouter.

Usage :
    python scripts/diagnostic_doublons_scenarios.py
"""
from sqlalchemy import text
from src.database.connection import engine

DEPARTEMENTS_A_INSPECTER = (
    "RH & Communication",
    "Réseau / Support Technique (NOC)",
    "Service Client",
)

if __name__ == "__main__":
    with engine.connect() as conn:
        print("=== Doublons exacts (même departement + nom_cas_usage) ===")
        doublons = conn.execute(text("""
            SELECT departement, nom_cas_usage, COUNT(*) as nb, array_agg(id ORDER BY id) as ids
            FROM scenarios
            GROUP BY departement, nom_cas_usage
            HAVING COUNT(*) > 1
            ORDER BY departement, nom_cas_usage
        """)).fetchall()

        if not doublons:
            print("  Aucun doublon exact trouvé.")
        for dep, nom, nb, ids in doublons:
            # Pour chaque id du doublon, combien d'exécutions ?
            details = []
            for sid in ids:
                nb_exec = conn.execute(
                    text("SELECT COUNT(*) FROM executions WHERE scenario_id = :sid"),
                    {"sid": sid},
                ).scalar()
                details.append(f"id={sid} ({nb_exec} exec)")
            print(f"  [{dep}] {nom!r} — {nb} copies : {', '.join(details)}")

        for dep in DEPARTEMENTS_A_INSPECTER:
            print(f"\n=== Détail : {dep} ===")
            rows = conn.execute(text("""
                SELECT id, nom_cas_usage,
                       (SELECT COUNT(*) FROM executions e WHERE e.scenario_id = scenarios.id) as nb_exec
                FROM scenarios
                WHERE departement = :dep
                ORDER BY nom_cas_usage
            """), {"dep": dep}).fetchall()
            print(f"  Total : {len(rows)} scénarios")
            for sid, nom, nb_exec in rows:
                print(f"    [{sid}] {nom} — {nb_exec} exécution(s)")