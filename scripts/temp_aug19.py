import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sqlalchemy import text
from src.database.connection import engine
from collections import defaultdict

# Find executions dated 2026-08-19 
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
