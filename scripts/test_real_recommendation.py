"""
Appelle directement la vraie fonction get_client_recommendation() du code de
production, pour chaque compte client existant, et affiche le resultat brut
+ des infos de debug supplementaires si le statut n'est pas "ready".

Usage:
  .venv\\Scripts\\python.exe scripts\\test_real_recommendation.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from src.database.connection import engine
from src.dashboard.queries import get_client_recommendation, get_client_department


def run():
    with engine.connect() as conn:
        clients = conn.execute(text(
            "SELECT email, departement, role FROM utilisateurs WHERE role = 'client'"
        )).fetchall()

    for email, dep, role in clients:
        print("=" * 80)
        print(f"CLIENT: {email}  (departement en base: {dep!r}, role: {role!r})")

        # Etape par etape, comme le fait vraiment get_client_recommendation()
        resolved_dep = get_client_department(email)
        print(f"  get_client_department('{email}') -> {resolved_dep!r}")

        result = get_client_recommendation(email)
        print(f"  get_client_recommendation('{email}') -> {result}")

        if result["status"] != "ready":
            print(f"  !!! STATUT NON 'ready': {result['status']} — voir le detail ci-dessous.")

            # Reproduit la 1ere requete (execution_count) telle quelle pour voir sa vraie valeur
            with engine.connect() as conn:
                execution_count = conn.execute(
                    text("""
                        WITH client_scope AS (
                            SELECT departement
                            FROM utilisateurs
                            WHERE email = :client_email
                              AND role = 'client'
                              AND departement IS NOT NULL
                        )
                        SELECT COUNT(e.id)
                        FROM client_scope cs
                        JOIN scenarios s ON s.departement = cs.departement
                        LEFT JOIN executions e ON e.scenario_id = s.id
                    """),
                    {"client_email": email},
                ).scalar()
                print(f"  execution_count (etape 1 du vrai code) = {execution_count}")
        print()


if __name__ == "__main__":
    run()