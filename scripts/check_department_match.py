"""
Compare les valeurs de departement stockees dans `utilisateurs` (comptes clients)
avec celles de `scenarios`, pour detecter un mismatch (espace, accent, encodage...).

Usage:
  .venv\\Scripts\\python.exe scripts\\check_department_match.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from src.database.connection import engine


def run():
    with engine.connect() as conn:
        print("=" * 80)
        print("Departements dans SCENARIOS (avec repr() pour voir les caracteres caches):")
        scenarios_deps = conn.execute(text(
            "SELECT DISTINCT departement FROM scenarios ORDER BY departement"
        )).fetchall()
        scenarios_set = set()
        for (dep,) in scenarios_deps:
            print(f"  {repr(dep)}")
            scenarios_set.add(dep)

        print()
        print("=" * 80)
        print("Comptes CLIENT dans utilisateurs, avec leur departement (repr()):")
        clients = conn.execute(text(
            "SELECT email, departement FROM utilisateurs WHERE role = 'client'"
        )).fetchall()

        if not clients:
            print("  Aucun compte client trouve.")
        for email, dep in clients:
            match = "OK - correspond exactement" if dep in scenarios_set else "!!! AUCUNE CORRESPONDANCE EXACTE !!!"
            print(f"  email={email!r:40} departement={dep!r:45} -> {match}")

        print()
        print("=" * 80)
        print("Departements presents dans scenarios mais AUCUN client ne les a exactement:")
        client_deps = {dep for _, dep in clients}
        for dep in scenarios_set:
            if dep not in client_deps:
                print(f"  {repr(dep)}  <- aucun compte client n'a cette valeur exacte")


if __name__ == "__main__":
    run()