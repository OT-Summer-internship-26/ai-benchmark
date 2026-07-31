from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT e.id, m.nom, e.latence_secondes, e.date_execution
            FROM executions e
            JOIN modeles m ON e.modele_id = m.id
            ORDER BY e.date_execution DESC
        """))
        print(f"{'ID':<5}{'Modèle':<30}{'Latence (s)':<15}{'Date'}")
        print("-" * 80)
        for row in result:
            print(f"{row[0]:<5}{row[1]:<30}{row[2]:<15.2f}{row[3]}")