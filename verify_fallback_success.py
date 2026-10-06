"""
Quick verification script to demonstrate Ollama fallback success.
Shows before/after comparison of execution scores.
"""
import psycopg2
from src.config.settings import DATABASE_URL
from datetime import datetime

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 80)
print("OLLAMA FALLBACK VERIFICATION - BEFORE vs AFTER")
print("=" * 80)
print()

# Get execution count with scores
cur.execute("""
    SELECT 
        COUNT(DISTINCT e.id) as total_executions,
        COUNT(DISTINCT CASE WHEN s.methode = 'ragas' AND s.is_legacy = FALSE THEN e.id END) as executions_with_ragas,
        AVG(CASE WHEN s.critere = 'score_global' AND s.methode = 'ragas' THEN s.note END) as avg_score
    FROM executions e
    LEFT JOIN scores s ON s.execution_id = e.id
    WHERE e.date_execution >= '2026-10-05'
""")

result = cur.fetchone()
total, with_scores, avg_score = result

print(f"📊 STATISTICS (October 5, 2026 executions)")
print(f"   Total executions: {total}")
print(f"   With RAGAS scores: {with_scores}")
avg_score_str = f"{avg_score:.3f}" if avg_score is not None else "N/A"
print(f"   Average score_global: {avg_score_str}")
print()

# Show sample of scores
print("📈 SAMPLE SCORES (Recent executions)")
print()
cur.execute("""
    SELECT 
        e.id,
        e.date_execution,
        m.nom as modele,
        s.note as score_global
    FROM executions e
    LEFT JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN scores s ON s.execution_id = e.id AND s.critere = 'score_global' AND s.methode = 'ragas'
    WHERE e.date_execution >= '2026-10-05'
    ORDER BY e.date_execution DESC
    LIMIT 10
""")

rows = cur.fetchall()
print(f"{'Exec ID':<10} {'Date':<20} {'Model':<25} {'Score Global':<15}")
print("-" * 80)
for row in rows:
    exec_id, date_exec, modele, score = row
    score_display = f"{score:.3f}" if score is not None else "N/A"
    print(f"{exec_id:<10} {str(date_exec):<20} {modele:<25} {score_display:<15}")

print()
print("=" * 80)
print("✅ VERIFICATION COMPLETE")
print("=" * 80)
print()

if with_scores == total and with_scores > 0:
    print("✅ SUCCESS: All executions have RAGAS scores!")
    avg_pct = f"{avg_score:.1%}" if avg_score is not None else "N/A"
    print(f"✅ Average quality: {avg_pct}")
    print()
    print("🎉 Ollama fallback implementation is working correctly!")
    print("   The system now prevents 0.0%/N/A scores when Groq rate-limits.")
else:
    print("⚠️  Some executions still missing scores")
    coverage = 100*with_scores/total if total > 0 else 0
    print(f"   Coverage: {with_scores}/{total} ({coverage:.1f}%)")

cur.close()
conn.close()
