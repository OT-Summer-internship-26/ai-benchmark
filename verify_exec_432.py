import psycopg2
from src.config.settings import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 60)
print("EXECUTION 432 - DETAILED SCORE VERIFICATION")
print("=" * 60)
print()

cur.execute("""
    SELECT s.critere, s.note, s.methode
    FROM scores s
    WHERE s.execution_id = 432
    ORDER BY s.critere
""")

scores = cur.fetchall()
print(f"Total scores for execution 432: {len(scores)}")
print()

ragas_scores = [s for s in scores if s[2] == 'ragas']
print(f"RAGAS scores: {len(ragas_scores)}")
for critere, note, methode in ragas_scores:
    print(f"  {critere:<20} {note:.3f}")

print()
print("=" * 60)

# Check for missing core metrics
core_metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
ragas_criteres = [s[0] for s in ragas_scores]
missing = [m for m in core_metrics if m not in ragas_criteres]

if missing:
    print(f"❌ MISSING: {', '.join(missing)}")
else:
    print("✅ ALL 4 CORE RAGAS METRICS PRESENT")

cur.close()
conn.close()
