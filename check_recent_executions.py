import psycopg2
from src.config.settings import DATABASE_URL
from datetime import datetime, timedelta

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Check recent executions from the last 7 days
print("=== RECENT EXECUTIONS (Last 7 days) ===\n")
cur.execute("""
    SELECT 
        e.id,
        e.date_execution,
        e.modele_id,
        LEFT(e.reponse_generee, 100) as reponse_preview,
        COUNT(s.id) as score_count,
        COUNT(CASE WHEN s.methode = 'ragas' AND s.is_legacy = FALSE THEN 1 END) as ragas_score_count
    FROM executions e
    LEFT JOIN scores s ON s.execution_id = e.id
    WHERE e.date_execution >= NOW() - INTERVAL '7 days'
    GROUP BY e.id, e.date_execution, e.modele_id, e.reponse_generee
    ORDER BY e.date_execution DESC
    LIMIT 20
""")

rows = cur.fetchall()
print(f"Found {len(rows)} executions in the last 7 days:\n")

for row in rows:
    exec_id, date_exec, modele_id, reponse_preview, score_count, ragas_count = row
    print(f"Execution ID: {exec_id}")
    print(f"  Date: {date_exec}")
    print(f"  Model ID: {modele_id}")
    print(f"  Response preview: {reponse_preview}...")
    print(f"  Total scores: {score_count}")
    print(f"  RAGAS scores (non-legacy): {ragas_count}")
    
    # Get detailed scores for this execution
    cur.execute("""
        SELECT critere, note, methode, is_legacy
        FROM scores
        WHERE execution_id = %s
        ORDER BY critere
    """, (exec_id,))
    
    scores = cur.fetchall()
    if scores:
        print(f"  Scores breakdown:")
        for score in scores:
            critere, note, methode, is_legacy = score
            legacy_flag = " (LEGACY)" if is_legacy else ""
            print(f"    - {critere}: {note} [{methode}{legacy_flag}]")
    else:
        print(f"  ⚠️  NO SCORES FOUND")
    print()

# Check for executions with missing RAGAS scores
print("\n=== EXECUTIONS WITHOUT RAGAS SCORES ===\n")
cur.execute("""
    SELECT 
        e.id,
        e.date_execution,
        e.modele_id,
        COUNT(s.id) FILTER (WHERE s.is_legacy = TRUE) as legacy_score_count
    FROM executions e
    LEFT JOIN scores s ON s.execution_id = e.id AND s.methode = 'ragas' AND s.is_legacy = FALSE
    WHERE e.date_execution >= NOW() - INTERVAL '7 days'
    GROUP BY e.id, e.date_execution, e.modele_id
    HAVING COUNT(s.id) = 0
    ORDER BY e.date_execution DESC
    LIMIT 10
""")

missing = cur.fetchall()
print(f"Found {len(missing)} executions without RAGAS scores:\n")
for row in missing:
    exec_id, date_exec, modele_id, legacy_count = row
    print(f"  Execution ID {exec_id} - {date_exec} - Model {modele_id} (has {legacy_count} legacy scores)")

cur.close()
conn.close()
