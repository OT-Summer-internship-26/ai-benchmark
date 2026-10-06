"""Check users table schema"""
from src.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name='users' 
        ORDER BY ordinal_position
    """))
    
    print("\n=== USERS TABLE SCHEMA ===")
    for row in result:
        print(f"{row.column_name:20s} {row.data_type:20s} {'NULL' if row.is_nullable == 'YES' else 'NOT NULL'}")
