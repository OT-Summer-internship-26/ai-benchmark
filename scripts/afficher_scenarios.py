from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM scenarios ORDER BY id"))
        colonnes = result.keys()

        for row in result:
            print("=" * 70)
            for col, val in zip(colonnes, row):
                print(f"{col} : {val}")
        print("=" * 70)