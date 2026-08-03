from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'scores'
            ORDER BY ordinal_position
        """))
        print(f"{'Colonne':<30}{'Type'}")
        print("-" * 50)
        for row in result:
            print(f"{row[0]:<30}{row[1]}")