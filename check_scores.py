"""Quick diagnostic: check if Ragas scores are NULL in database"""
import sqlite3

conn = sqlite3.connect("data/ai_benchmark.db")
cursor = conn.cursor()

# First, list all tables
print("=== TABLES IN DATABASE ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

# Check executions table structure
print("\n=== EXECUTIONS TABLE STRUCTURE ===")
cursor.execute("PRAGMA table_info(executions)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]:30s} {col[2]:15s} {'NOT NULL' if col[3] else ''}")

# Check last 10 scores
print("\n=== LAST 10 EXECUTIONS WITH SCORES ===")
print("\n=== LAST 10 EXECUTIONS WITH SCORES ===")
cursor.execute("""
    SELECT 
        e.id,
        m.nom as model,
        e.faithfulness,
        e.answer_relevancy,
        e.context_precision,
        e.context_recall,
        e.score_global_auto
    FROM executions e
    JOIN modeles m ON e.model_id = m.id
    ORDER BY e.id DESC
    LIMIT 10
""")

rows = cursor.fetchall()
for row in rows:
    print(f"ID {row[0]:3d} | {row[1]:25s} | F:{row[2]} AR:{row[3]} CP:{row[4]} CR:{row[5]} Global:{row[6]}")

# Count NULL vs non-NULL
print("\n=== STATISTICS ===")
cursor.execute("SELECT COUNT(*) FROM executions WHERE faithfulness IS NULL")
null_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM executions WHERE faithfulness IS NOT NULL")
notnull_count = cursor.fetchone()[0]

print(f"Executions with NULL faithfulness: {null_count}")
print(f"Executions with valid faithfulness: {notnull_count}")

conn.close()
