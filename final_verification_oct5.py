"""
Final verification for all October 5, 2026 executions.
Confirms all have complete RAGAS scores (no N/A metrics).
"""
import psycopg2
from src.config.settings import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 80)
print("FINAL VERIFICATION - OCTOBER 5, 2026 EXECUTIONS")
print("=" * 80)
print()

# Get all Oct 5 executions with their score counts
cur.execute("""
    WITH ragas_scores AS (
        SELECT 
            execution_id,
            COUNT(*) FILTER (WHERE critere = 'faithfulness') as has_faithfulness,
            COUNT(*) FILTER (WHERE critere = 'answer_relevancy') as has_answer_relevancy,
            COUNT(*) FILTER (WHERE critere = 'context_precision') as has_context_precision,
            COUNT(*) FILTER (WHERE critere = 'context_recall') as has_context_recall,
            COUNT(*) as total_scores
        FROM scores
        WHERE methode = 'ragas' AND is_legacy = FALSE
        GROUP BY execution_id
    )
    SELECT 
        e.id,
        e.scenario_id,
        m.nom as modele,
        COALESCE(rs.total_scores, 0) as total_scores,
        COALESCE(rs.has_faithfulness, 0) as has_faithfulness,
        COALESCE(rs.has_answer_relevancy, 0) as has_answer_relevancy,
        COALESCE(rs.has_context_precision, 0) as has_context_precision,
        COALESCE(rs.has_context_recall, 0) as has_context_recall
    FROM executions e
    LEFT JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN ragas_scores rs ON rs.execution_id = e.id
    WHERE e.date_execution >= '2026-10-05' AND e.date_execution < '2026-10-06'
    ORDER BY e.id
""")

executions = cur.fetchall()

print(f"📊 FOUND {len(executions)} EXECUTIONS FROM OCTOBER 5, 2026")
print()

complete_count = 0
incomplete_count = 0
incomplete_list = []

for exec_id, scenario_id, modele, total, has_f, has_a, has_c_p, has_c_r in executions:
    is_complete = has_f > 0 and has_a > 0 and has_c_p > 0 and has_c_r > 0
    
    if is_complete:
        complete_count += 1
        status = "✅"
    else:
        incomplete_count += 1
        status = "❌"
        missing = []
        if has_f == 0: missing.append("faithfulness")
        if has_a == 0: missing.append("answer_relevancy")
        if has_c_p == 0: missing.append("context_precision")
        if has_c_r == 0: missing.append("context_recall")
        incomplete_list.append((exec_id, missing))
    
    print(f"{status} Execution {exec_id:<4} (Scenario {scenario_id:<3}) - {total} scores - {modele}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ Complete executions:   {complete_count}/{len(executions)} ({100*complete_count/len(executions):.1f}%)")
print(f"❌ Incomplete executions: {incomplete_count}/{len(executions)}")
print()

if incomplete_list:
    print("⚠️  EXECUTIONS WITH MISSING METRICS:")
    for exec_id, missing in incomplete_list:
        print(f"  - Execution {exec_id}: missing {', '.join(missing)}")
    print()
    print("❌ VERIFICATION FAILED - Some executions still have N/A metrics")
else:
    print("🎉 SUCCESS - ALL EXECUTIONS HAVE COMPLETE RAGAS SCORES!")
    print("   No more N/A metrics in Streamlit UI for October 5th data.")

print()
print("=" * 80)

cur.close()
conn.close()
