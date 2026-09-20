import sys, io, pathlib
sys.path.insert(0, str(pathlib.Path('.').resolve()))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sqlalchemy import text
from src.database.connection import engine
from collections import defaultdict

# Find executions dated 2026-08-19 (the ones the log shows as all-None)
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT e.id, e.date_execution, s.departement, s.nom_cas_usage, m.nom
        FROM executions e
        JOIN scenarios s ON s.id = e.scenario_id
        JOIN modeles m ON m.id = e.modele_id
        WHERE e.date_execution::date = '2026-08-19'
        ORDER BY e.id
    """)).fetchall()

print("Executions from 2026-08-19: {}".format(len(rows)))
for r in rows:
    print("  exec_id={} | {} | {} | {}".format(r[0], str(r[1])[:19], r[2], r[4]))

if rows:
    ids = [r[0] for r in rows]
    with engine.connect() as conn:
        scores = conn.execute(text("""
            SELECT execution_id, critere, note
            FROM scores
            WHERE execution_id = ANY(:ids)
            ORDER BY execution_id, critere
        """), {'ids': ids}).fetchall()
    
    score_map = defaultdict(dict)
    for eid, crit, note in scores:
        score_map[eid][crit] = note
    
    print("Scores for Aug 19 executions:")
    for eid in ids:
        s = score_map.get(eid, {})
        def v(k):
            return str(s.get(k, 'MISSING'))
        print("  exec_id={}: faith={} ar={} cp={} cr={}".format(
            eid, v('faithfulness'), v('answer_relevancy'), v('context_precision'), v('context_recall')))

print()
# Now check what the Aug 19 evaluator actually evaluated -- look at executions from then
# Also check if chunks_rag would have been empty due to the vector store psycopg SyntaxError shown in log (Aug 17)
print("The log shows psycopg2 SyntaxError in vector_store.py on 2026-08-17 for IT dept.")
print("This would have caused empty chunks_rag for ALL scenarios that day.")
print("Aug 19 executions with empty chunks_rag -> evaluateur calls evaluer_execution_ragas with []")
print("-> faithfulness/context_precision/context_recall all get empty context -> judge called but returns note.")
print()
print("WAIT - looking at the log output: ALL metrics including answer_relevancy were None on Aug 19.")
print("answer_relevancy does NOT need RAG context. So judge itself was failing, not RAG.")
print()

# Let's understand: which executions from Aug 19 do NOT have scores at all?
# Compare to bucket C
c_ids_aug19 = []
for r in rows:
    eid = r[0]
    s = score_map.get(eid, {})
    if 'faithfulness' not in s:
        c_ids_aug19.append(eid)
        
print("Aug 19 executions with NO faithfulness score (bucket C candidates): {}".format(c_ids_aug19))
