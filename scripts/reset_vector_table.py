from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM documents_vectorises"))
        avant = result.scalar()
        
        conn.execute(text("DELETE FROM documents_vectorises"))
        conn.commit()
        
        print(f"✅ {avant} chunks supprimés. Table vidée.")