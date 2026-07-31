from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT departement, COUNT(*) as nb_chunks FROM documents_vectorises GROUP BY departement ORDER BY departement"
        ))
        print(f"{'Département':<40}{'Nb chunks'}")
        print("-" * 55)
        total = 0
        for row in result:
            print(f"{row[0]:<40}{row[1]}")
            total += row[1]
        print("-" * 55)
        print(f"{'TOTAL':<40}{total}")