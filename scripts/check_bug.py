from src.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT execution_id, critere, note
        FROM scores
        ORDER BY execution_id, critere
    """))
    for row in result:
        print(row)