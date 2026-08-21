"""Liste tous les scénarios dont le departement est 'Agents IA et Automatisation'
ou 'Conseiller Service Client', avec leur metier et leur nombre d'exécutions,
pour décider vers quel département existant les réassigner.

Usage :
    python scripts/diagnostic_departements_a_corriger.py
"""
from sqlalchemy import text
from src.database.connection import engine

DEPARTEMENTS_A_CORRIGER = ("Agents IA et Automatisation", "Conseiller Service Client")

if __name__ == "__main__":
    with engine.connect() as conn:
        print("=== Départements valides actuellement en base (hors ceux à corriger) ===")
        valides = conn.execute(text("""
            SELECT departement, COUNT(*) as nb_scenarios
            FROM scenarios
            WHERE departement NOT IN :a_corriger
            GROUP BY departement
            ORDER BY departement
        """), {"a_corriger": DEPARTEMENTS_A_CORRIGER}).fetchall()
        for dep, nb in valides:
            print(f"  {dep} — {nb} scénarios")

        print(f"\n=== Scénarios à corriger (departement dans {DEPARTEMENTS_A_CORRIGER}) ===")
        rows = conn.execute(text("""
            SELECT id, departement, metier, nom_cas_usage,
                   (SELECT COUNT(*) FROM executions e WHERE e.scenario_id = scenarios.id) as nb_executions
            FROM scenarios
            WHERE departement IN :a_corriger
            ORDER BY departement, nom_cas_usage
        """), {"a_corriger": DEPARTEMENTS_A_CORRIGER}).fetchall()

        if not rows:
            print("  Aucun scénario trouvé avec ces valeurs de departement.")
        for sid, dep, metier, nom, nb_exec in rows:
            print(f"  [{sid}] departement={dep!r} | metier={metier!r} | {nom} | {nb_exec} exécution(s)")