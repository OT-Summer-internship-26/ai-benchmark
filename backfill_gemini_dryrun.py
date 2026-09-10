#!/usr/bin/env python3
"""
Dry-run backfill for Gemini 3.1 Flash-Lite executions.
Will show what would be inserted WITHOUT applying changes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

from sqlalchemy import text
from src.database.connection import engine
from src.evaluation.deepeval_runner import evaluer_execution_ragas
from src.rag.vector_store import search_similar

# Gemini execution IDs (confirmed no scores)
GEMINI_EXEC_IDS = [74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]

print("="*80)
print("🔍 DRY-RUN: Backfill Gemini Executions")
print("="*80)
print(f"\nExecution IDs to evaluate: {GEMINI_EXEC_IDS}")
print(f"Total: {len(GEMINI_EXEC_IDS)} executions\n")

def fetch_execution(conn, exec_id: int):
    q = text("""
        SELECT e.id, e.scenario_id, e.reponse_generee as reponse, e.modele_id,
               m.nom as modele_nom, e.date_execution
        FROM executions e JOIN modeles m ON m.id=e.modele_id
        WHERE e.id = :eid
    """)
    return conn.execute(q, {"eid": exec_id}).mappings().first()

def fetch_scenario(conn, scenario_id: int):
    q = text("""
        SELECT id, nom_cas_usage, prompt, sortie_attendue, departement
        FROM scenarios WHERE id = :sid
    """)
    row = conn.execute(q, {"sid": scenario_id}).mappings().first()
    if not row:
        return None
    scenario = dict(row)
    try:
        chunks = search_similar(query=scenario.get("prompt", ""), departement=scenario.get("departement", ""), top_k=8)
    except Exception as e:
        print(f"⚠️  RAG search failed for scenario {scenario_id}: {e}")
        chunks = []
    scenario["chunks_rag"] = chunks
    return scenario

# Simulate evaluation
total_scenarios = 0
total_scores_to_insert = 0
failed_count = 0

with engine.connect() as conn:
    for exec_id in GEMINI_EXEC_IDS:
        try:
            execution = fetch_execution(conn, exec_id)
            if not execution:
                print(f"❌ Execution {exec_id} not found")
                failed_count += 1
                continue
            
            scenario = fetch_scenario(conn, execution['scenario_id'])
            if not scenario:
                print(f"❌ Scenario for execution {exec_id} not found")
                failed_count += 1
                continue
            
            # Evaluate
            resultat = evaluer_execution_ragas(
                reponse=execution['reponse'],
                question=scenario.get('prompt', ''),
                contexte_chunks=scenario.get('chunks_rag', []),
                sortie_attendue=scenario.get('sortie_attendue')
            )
            
            # Count scores to insert
            scores_to_insert = 0
            for critere in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                detail = resultat.get(critere, {})
                if detail.get('note') is not None:
                    scores_to_insert += 1
            
            if resultat.get('score_global') is not None:
                scores_to_insert += 1
            
            print(f"✅ exec_id={exec_id} | {scenario['nom_cas_usage'][:30]:30} | {scores_to_insert} scores")
            
            # Print metric details
            for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                detail = resultat[metric]
                note = detail.get('note')
                status = f"✅ {note:.3f}" if note is not None else "⚠️  None"
                print(f"   {metric:20}: {status}")
            
            total_scenarios += 1
            total_scores_to_insert += scores_to_insert
            
        except Exception as e:
            print(f"❌ Error processing execution {exec_id}: {e}")
            failed_count += 1

print("\n" + "="*80)
print("DRY-RUN SUMMARY")
print("="*80)
print(f"\n📊 Results:")
print(f"   Successfully evaluated: {total_scenarios}/{len(GEMINI_EXEC_IDS)}")
print(f"   Failed: {failed_count}")
print(f"   Total scores to insert: {total_scores_to_insert}")
print(f"   Average scores per execution: {total_scores_to_insert / max(1, total_scenarios):.1f}")

print(f"\n✅ IF THIS LOOKS GOOD, RUN:")
print(f"   python scripts/re_evaluate_executions.py --ids {','.join(map(str, GEMINI_EXEC_IDS))} --apply")
