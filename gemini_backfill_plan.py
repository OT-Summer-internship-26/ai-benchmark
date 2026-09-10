#!/usr/bin/env python3
"""
Backfill plan for Gemini 3.1 Flash-Lite executions.
Shows exactly what WILL be backfilled WITHOUT making live API calls.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

print("="*100)
print("📋 GEMINI 3.1 FLASH-LITE BACKFILL PLAN")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*100)

# Exact execution IDs from 2026-08-20 (confirmed unevaluated)
GEMINI_EXEC_IDS = [74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]

print(f"\n📋 Execution IDs to backfill: {GEMINI_EXEC_IDS}")
print(f"Total: {len(GEMINI_EXEC_IDS)} executions\n")

# Verify all executions exist and have no scores
query = text("""
    SELECT 
        e.id AS execution_id,
        m.nom AS model_name,
        s.nom_cas_usage AS scenario_name,
        s.departement,
        LENGTH(COALESCE(e.reponse_generee, '')) AS response_length,
        LENGTH(COALESCE(s.prompt, '')) AS prompt_length,
        LENGTH(COALESCE(s.sortie_attendue, '')) AS sortie_length,
        CASE 
            WHEN e.reponse_generee IS NULL THEN 'NULL'
            WHEN LENGTH(e.reponse_generee) < 10 THEN 'TOO_SHORT'
            ELSE 'VALID'
        END AS response_status,
        CASE
            WHEN s.sortie_attendue IS NULL OR LENGTH(s.sortie_attendue) = 0 THEN 'MISSING'
            ELSE 'PRESENT'
        END AS sortie_status,
        (SELECT COUNT(*) FROM scores WHERE execution_id = e.id) AS existing_scores
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE e.id IN ({})
    ORDER BY e.id
""".format(','.join(map(str, GEMINI_EXEC_IDS))))

with engine.connect() as conn:
    results = conn.execute(query).fetchall()

print("BACKFILL PLAN:")
print("="*100)
print(f"{'ID':4} | {'Model':25} | {'Scenario':35} | {'Dept':20} | {'Resp':5} | {'Sortie':8} | {'Existing'}")
print("-"*100)

total_to_backfill = 0
issues = []

for row in results:
    exec_id, model, scenario, dept, resp_len, prompt_len, sortie_len, resp_status, sortie_status, existing_scores = row
    
    # Check for issues
    issue_flags = []
    
    if resp_status != 'VALID':
        issue_flags.append(f"Response {resp_status}")
    
    if sortie_status == 'MISSING':
        issue_flags.append("No expected output")
    
    if existing_scores > 0:
        issue_flags.append(f"Already has {existing_scores} scores")
    
    # Determine if can backfill
    can_backfill = (resp_status == 'VALID' and existing_scores == 0)
    
    if can_backfill:
        total_to_backfill += 1
        status = "✅ CAN BACKFILL"
        resp_display = f"{resp_len:4}c"
        sortie_display = sortie_status[:6]
    else:
        status = "⚠️ SKIP"
        resp_display = resp_status[:5]
        sortie_display = sortie_status[:6]
    
    print(f"{exec_id:4} | {model[:25]:25} | {scenario[:35]:35} | {dept[:20]:20} | {resp_display} | {sortie_display} | {existing_scores:8}")
    
    if issue_flags:
        issues.append((exec_id, issue_flags))

print("\n" + "="*100)
print("📊 BACKFILL SUMMARY")
print("="*100)

print(f"\n✅ Executions ready to backfill: {total_to_backfill}/{len(GEMINI_EXEC_IDS)}")
print(f"❌ Cannot backfill: {len(GEMINI_EXEC_IDS) - total_to_backfill}")

if issues:
    print(f"\n⚠️  Issues found:")
    for exec_id, issue_list in issues:
        print(f"   exec_id {exec_id}: {', '.join(issue_list)}")

# Show expected insertion details
print(f"\n" + "="*100)
print("EXPECTED SCORE INSERTIONS")
print("="*100)

print(f"""
For each backfilled execution, the script will insert:

✅ faithfulness (note: 0.0-1.0)
✅ answer_relevancy (note: 0.0-1.0)
✅ context_precision (note: 0.0-1.0)
✅ context_recall (note: 0.0-1.0, or None if sortie_attendue is empty)
✅ score_global (note: average of above)

Expected total insertions: ~{total_to_backfill * 5} score rows
   ({total_to_backfill} executions × ~5 metrics per execution)

Special case - context_recall:
   - Returns None if sortie_attendue is empty (by design)
   - These executions have sortie_attendue present, so context_recall should be scored

Data flow during backfill:
   1. Fetch execution (response_generee)
   2. Fetch scenario (prompt, sortie_attendue, departement)
   3. Retrieve context chunks via search_similar() (RAG)
   4. Call evaluer_execution_ragas() with:
      - reponse = execution.reponse_generee
      - question = scenario.prompt
      - contexte_chunks = chunks from RAG
      - sortie_attendue = scenario.sortie_attendue
   5. For each metric with note != None, insert to scores table
""")

# Show the exact command
ids_str = ','.join(map(str, GEMINI_EXEC_IDS))

print(f"\n" + "="*100)
print("COMMAND TO RUN BACKFILL")
print("="*100)

print(f"""
When ready to apply (AFTER YOUR CONFIRMATION):

   python scripts/re_evaluate_executions.py --ids {ids_str} --apply

This will:
1. Fetch each execution and scenario data
2. Retrieve context chunks via RAG search
3. Evaluate all 4 RAGAS metrics using LLM judge
4. Insert scores to database

⚠️  IMPORTANT: This will make multiple API calls to Groq for LLM judge
   (4 calls × 16 executions = ~64 API calls total)
   Groq rate limit: 3 retries with backoff, so expect API errors on rate limit

Do NOT run yet - wait for your confirmation after reviewing this plan!
""")
