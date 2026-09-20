import sys, io, pathlib
sys.path.insert(0, str(pathlib.Path('.').resolve()))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from sqlalchemy import text
from src.database.connection import engine
from collections import defaultdict

# The Aug 19 log showed 11 evaluations all skipped. But executions 57-68 mostly HAVE scores.
# That means the Aug 19 log (10:42-11:12) corresponds to a DIFFERENT set of executions.
# Let's find which executions those were by checking date_execution closer to 10:42

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT e.id, e.date_execution, s.departement, s.nom_cas_usage, m.nom
        FROM executions e
        JOIN scenarios s ON s.id = e.scenario_id
        JOIN modeles m ON m.id = e.modele_id
        WHERE e.date_execution >= '2026-08-19 10:00:00' AND e.date_execution < '2026-08-19 12:00:00'
        ORDER BY e.id
    """)).fetchall()

print("Executions from Aug 19 10:00-12:00 (log evaluator run time): {}".format(len(rows)))
for r in rows:
    print("  exec_id={} | {} | {} | {}".format(r[0], str(r[1])[:19], r[2], r[4]))

# The all-None Skipping block in log is from 10:45-11:12 evaluating 11 executions.
# These executions must be from a prior batch (possibly July 30 or Aug 3 ones re-evaluated?
# Or they were inserted WITHOUT scores.

# Let's check what the all-None entries share -- look at the ones in bucket C from early dates
# that were re-evaluated in the Aug 19 run context
print()
print("Looking for executions where chunks_rag would be empty (e.g., Service Client or early batch)...")
with engine.connect() as conn:
    service_client = conn.execute(text("""
        SELECT e.id, e.date_execution, s.nom_cas_usage, m.nom,
               (SELECT COUNT(*) FROM documents_vectorises WHERE departement = s.departement) as chunks
        FROM executions e
        JOIN scenarios s ON s.id = e.scenario_id
        JOIN modeles m ON m.id = e.modele_id
        WHERE s.departement = 'Service Client'
        ORDER BY e.id
    """)).fetchall()
print("Service Client executions (has 0 chunks in vector store):")
for r in service_client:
    print("  exec_id={} | {} | chunks_for_dept={} | {}".format(r[0], str(r[1])[:19], r[4], r[2]))

# Check Service Client scores
ids = [r[0] for r in service_client]
with engine.connect() as conn:
    scores = conn.execute(text("""
        SELECT execution_id, critere, note FROM scores
        WHERE execution_id = ANY(:ids) ORDER BY execution_id, critere
    """), {'ids': ids}).fetchall()
score_map = defaultdict(dict)
for eid, crit, note in scores:
    score_map[eid][crit] = note
print("Scores for Service Client:")
for r in service_client:
    eid = r[0]
    s = score_map.get(eid, {})
    print("  exec_id={}: faith={} ar={} cp={} cr={}".format(
        eid, s.get('faithfulness','MISS'), s.get('answer_relevancy','MISS'), 
        s.get('context_precision','MISS'), s.get('context_recall','MISS')))
