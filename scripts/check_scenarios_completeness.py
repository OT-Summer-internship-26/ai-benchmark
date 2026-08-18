import sys
from pathlib import Path

# Ajoute la racine du projet au path pour que "src" soit importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import engine
from sqlalchemy import text

DEPARTEMENTS_ATTENDUS = [
    "RH & Communication", "Marketing & Digital", "IT & Architecture",
    "Réseau / Support Technique (NOC)", "Productivité Personnelle",
    "Agents IA et Automatisation",
]
CIBLE = 16

if __name__ == "__main__":
    with engine.connect() as conn:
        for dep in DEPARTEMENTS_ATTENDUS:
            count = conn.execute(
                text("SELECT COUNT(*) FROM scenarios WHERE departement = :d"),
                {"d": dep},
            ).scalar()
            statut = "✅" if count >= CIBLE else f"❌ manque {CIBLE - count}"
            print(f"{dep:<40} {count:>3} scénarios {statut}")