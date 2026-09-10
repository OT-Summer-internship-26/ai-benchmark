#!/usr/bin/env python3
"""
Backfill RAGAS scores for 16 Gemini 3.1 Flash-Lite executions.
Uses inspect_and_insert.py logic to show dry-run output.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

from sqlalchemy import text
from src.database.connection import engine
from src.evaluation.deepeval_runner import evaluer_execution_ragas
from src.rag.vector_store import search_similar

print("="*100)
print("🔄 GEMINI 3.1 FLASH-LITE BACKFILL DRY-RUN")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*100)

# Exact execution IDs from 2026-08-20 (confirmed unevaluated)
GEMINI_EXEC_IDS = [74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]

print(f"\n📋 Execution IDs to backfill: {GEMINI_EXEC_IDS}")
print(f"Total: {len(GEMINI_EXEC_IDS)} executions\n")

def fetch_execution(conn, exec_id: int):
    """Fetch execution with all needed data."""
    q = text("""
        SELECT 
            e.id, 
            e.scenario_id, 
            e.reponse_generee, 
            e.modele_id,
            m.nom as modele_nom,
            e.date_execution
        FROM executions e 
        JOIN modeles m ON m.id = e.modele_id
        WHERE e.id = :eid
    """)
    return conn.execute(q, {"eid": exec_id}).mappings().first()

def fetch_scenario(conn, scenario_id: int):
    """Fetch scenario with RAG context."""
    q = text("""
        SELECT id, nom_cas_usage, prompt, sortie_attendue, departement
        FROM scenarios 
        WHERE id = :sid
    """)
    row = conn.execute(q, {"sid": scenario_id}).mappings().first()
    
    if not row:
        return None
    
    scenario = dict(row)
    
    # Retrieve chunks via RAG (same as pipeline)
    try:
        chunks = search_similar(
            query=scenario.get("prompt", ""),
            departement=scenario.get("departement", ""),
            top_k=8
        )
        scenario["chunks_rag"] = chunks
    except Exception as e:
        print(f"      ⚠️  RAG search failed: {e}")
        scenario["chunks_rag"] = []
    
    return scenario

def count_existing_scores(conn, exec_id: int):
    """Count existing scores for an execution."""
    q = text("""
        SELECT COUNT(*) 
        FROM scores 
        WHERE execution_id = :exec_id
    """)
    return conn.execute(q, {"exec_id": exec_id}).scalar()

# Dry-run evaluation
print("EVALUATION DRY-RUN:")
print("=" * 100)

total_scores_to_insert = 0
evaluation_results = []

with engine.connect() as conn:
    for i, exec_id in enumerate(GEMINI_EXEC_IDS, 1):
        print(f"\n[{i}/{len(GEMINI_EXEC_IDS)}] Execution ID: {exec_id}")
        
        try:
            # Check if already has scores
            existing_count = count_existing_scores(conn, exec_id)
            if existing_count > 0:
                print(f"      ⚠️  Already has {existing_count} score(s) - skipping")
                continue
            
            # Fetch execution
            execution = fetch_execution(conn, exec_id)
            if not execution:
                print(f"      ❌ Execution not found")
                continue
            
            # Fetch scenario
            scenario = fetch_scenario(conn, execution['scenario_id'])
            if not scenario:
                print(f"      ❌ Scenario not found")
                continue
            
            print(f"      Model: {execution['modele_nom']}")
            print(f"      Scenario: {scenario['nom_cas_usage'][:50]}")
            print(f"      Department: {scenario['departement']}")
            print(f"      Response length: {len(execution.get('reponse_generee', '') or '')} chars")
            print(f"      Context chunks: {len(scenario.get('chunks_rag', []))} chunks")
            print(f"      Sortie_attendue: {'Yes' if scenario.get('sortie_attendue') else 'No'}")
            
            # Evaluate
            print(f"      Evaluating...", end=" ")
            resultat = evaluer_execution_ragas(
                reponse=execution['reponse_generee'],
                question=scenario.get('prompt', ''),
                contexte_chunks=scenario.get('chunks_rag', []),
                sortie_attendue=scenario.get('sortie_attendue')
            )
            
            # Count scores to insert
            scores_to_insert = []
            
            # Check each metric
            for critere in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                detail = resultat.get(critere, {})
                note = detail.get('note')
                justification = detail.get('justification', '')[:500]
                
                if note is not None:
                    scores_to_insert.append({
                        'critere': critere,
                        'note': note,
                        'justification': justification
                    })
                    print(f"✓", end="")
                else:
                    print(f"✗", end="")
            
            # Check global score
            global_score = resultat.get('score_global')
            if global_score is not None:
                scores_to_insert.append({
                    'critere': 'score_global',
                    'note': global_score,
                    'justification': 'Moyenne des 4 métriques Ragas disponibles'
                })
                print(f"✓", end="")
            else:
                print(f"✗", end="")
            
            print()
            
            print(f"\n      📊 Scores to insert: {len(scores_to_insert)}")
            for score in scores_to_insert:
                note_display = f"{score['note']:.3f}" if isinstance(score['note'], float) else score['note']
                print(f"         - {score['critere']:20}: {note_display}")
            
            total_scores_to_insert += len(scores_to_insert)
            evaluation_results.append({
                'exec_id': exec_id,
                'model': execution['modele_nom'],
                'scenario': scenario['nom_cas_usage'],
                'scores_count': len(scores_to_insert),
                'scores': scores_to_insert,
                'status': 'OK'
            })
            
        except Exception as e:
            print(f"      ❌ Error: {type(e).__name__}: {str(e)[:100]}")
            evaluation_results.append({
                'exec_id': exec_id,
                'status': 'ERROR',
                'error': str(e)
            })

# Summary
print("\n" + "="*100)
print("📊 DRY-RUN SUMMARY")
print("="*100)

successful = sum(1 for r in evaluation_results if r.get('status') == 'OK')
failed = sum(1 for r in evaluation_results if r.get('status') == 'ERROR')

print(f"\n✅ Successfully evaluated: {successful}/{len(GEMINI_EXEC_IDS)}")
print(f"❌ Failed: {failed}")
print(f"📈 Total scores to insert: {total_scores_to_insert}")
print(f"   Average per execution: {total_scores_to_insert / max(1, successful):.1f} scores")

# Summary table
print("\n" + "-"*100)
print("DETAILED RESULTS:")
print("-"*100)
print(f"{'Exec ID':8} | {'Model':25} | {'Scenario':40} | {'Status':10} | {'Scores'}")
print("-"*100)

for result in evaluation_results:
    if result.get('status') == 'OK':
        exec_id = result['exec_id']
        model = result['model'][:25]
        scenario = result['scenario'][:40]
        scores_count = result['scores_count']
        print(f"{exec_id:8} | {model:25} | {scenario:40} | {'✅ OK':10} | {scores_count}")
    else:
        exec_id = result['exec_id']
        error = result.get('error', 'Unknown')[:20]
        print(f"{exec_id:8} | {'':25} | {'':40} | {'❌ ERROR':10} | {error}")

# Show what command to run
print("\n" + "="*100)
print("🔧 NEXT STEPS")
print("="*100)

ids_str = ','.join(map(str, GEMINI_EXEC_IDS))

print(f"\n✅ If results above look good, apply with:")
print(f"\n   python scripts/re_evaluate_executions.py --ids {ids_str} --apply")
print(f"\n⚠️  Wait for user confirmation before applying!")
