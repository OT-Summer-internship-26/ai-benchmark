import psycopg2
from src.config.settings import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get executions table schema
print("=== EXECUTIONS TABLE SCHEMA ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='executions' 
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n=== SCORES TABLE SCHEMA ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name='scores' 
    ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

cur.close()
conn.close()
