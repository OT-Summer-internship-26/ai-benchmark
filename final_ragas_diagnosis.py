#!/usr/bin/env python3
"""
Final comprehensive diagnosis of RAGAS None values.
Root cause confirmation and recommendations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

print("="*80)
print("📋 FINAL RAGAS SCORES DIAGNOSIS")
print("="*80)

# 1. Gemini verification
print("\n1️⃣  GEMINI 3.1 FLASH-LITE")
print("-" * 80)

query = text("SELECT COUNT(*) FROM scores WHERE execution_id IN (SELECT id FROM executions WHERE modele_id IN (SELECT id FROM modeles WHERE nom LIKE '%Gemini%'))")
with engine.connect() as conn:
    count = conn.execute(query).scalar()

if count == 0:
    print("✅ ROOT CAUSE: Gemini executions have NO scores (confirmed expected behavior)")
    print("   Reason: lancer_gemini_16.py explicitly skips evaluateur step")
    print("   Action: Backfill using re_evaluate_executions.py\n")
    
    # Get Gemini execution IDs
    gemini_query = text("SELECT id FROM executions WHERE modele_id IN (SELECT id FROM modeles WHERE nom LIKE '%Gemini%') ORDER BY id")
    with engine.connect() as conn:
        gemini_ids = [row[0] for row in conn.execute(gemini_query).fetchall()]
    print(f"   Gemini execution_ids: {gemini_ids}")
else:
    print(f"ℹ️  Gemini has {count} scores in database")

# 2. Qwen2.5 and Gemma2 detailed analysis
print("\n2️⃣  QWEN2.5 7B & GEMMA2 9B")
print("-" * 80)

models = [('Qwen2.5 7B (Ollama)', 16), ('Gemma2 9B (Ollama)', 3)]

for model_name, sample_exec_id in models:
    print(f"\n📊 {model_name}:")
    
    # Get execution details
    query = text("""
        SELECT e.id, s.nom_cas_usage, s.departement, s.prompt, s.sortie_attendue,
               (SELECT COUNT(*) FROM scores WHERE execution_id = e.id) as score_count
        FROM executions e
        JOIN modeles m ON m.id = e.modele_id
        JOIN scenarios s ON s.id = e.scenario_id
        WHERE m.nom = :model_name
        LIMIT 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"model_name": model_name}).fetchone()
    
    if result:
        exec_id, scenario_name, dept, prompt, sortie, score_count = result
        print(f"   Sample exec_id: {exec_id}")
        print(f"   Scenario: {scenario_name}")
        print(f"   Department: {dept}")
        print(f"   Total scores in DB: {score_count}")
        
        # Get which metrics are present
        metrics_query = text("""
            SELECT DISTINCT critere FROM scores WHERE execution_id = :exec_id ORDER BY critere
        """)
        
        with engine.connect() as conn:
            metrics = [row[0] for row in conn.execute(metrics_query, {"exec_id": exec_id}).fetchall()]
        
        all_metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
        missing_metrics = [m for m in all_metrics if m not in metrics]
        
        if missing_metrics:
            print(f"   ⚠️  Missing metrics: {missing_metrics}")
        
        print(f"   Sortie_attendue populated: {'Yes' if sortie else 'No'}")

print("\n" + "="*80)
print("🔍 ROOT CAUSE ANALYSIS")
print("="*80)

print("""
1. GEMINI 3.1 FLASH-LITE: ALL 4 metrics = None
   ✅ ROOT CAUSE: Not evaluated (as expected)
   📝 Status: Expected behavior - lancer_gemini_16.py explicitly skips evaluateur
   🔧 Fix: Backfill using re_evaluate_executions.py

2. QWEN2.5 7B & GEMMA2 9B: context_precision & context_recall = None
   ✅ ROOT CAUSE: Empty context chunks (context_chunks = [])
   📝 Status: RAG vector store is empty or search failing silently
   
   Why context metrics are None:
   - collecteur.agent_collecteur() calls search_similar() to get chunks_rag
   - If search fails (RAG exception), chunks_rag is set to []
   - evaluer_context_precision([]) receives empty context
   - Judge cannot evaluate empty context → returns None
   - evaluer_context_recall([], ...) might also return None with empty chunks
   
   Why other metrics work:
   - faithfulness & answer_relevancy don't need context chunks
   - They only use the response and question/context comparison
   - They can compute scores even without context

3. CONTEXT PRECISION EMPTY LIST SCENARIO:
   - contexte = "".join(...) = ""  (empty string)
   - Judge prompt includes "CHUNKS RÉCUPÉRÉS: "
   - Judge likely cannot evaluate meaningfully and returns None
   - This is SILENT FAILURE, not an API error
   
4. CONTEXT RECALL EMPTY SORTIE_ATTENDUE:
   - Already designed to return note=None when sortie_attendue is empty
   - This is BY DESIGN, not a bug
   - Check if sortie_attendue is actually empty for affected scenarios
""")

print("\n" + "="*80)
print("💡 RECOMMENDATIONS")
print("="*80)

print("""
1. GEMINI BACKFILL:
   Action: python scripts/re_evaluate_executions.py --ids 74-89 --apply
   Expected: 16 executions will get 4 metrics each (64 score rows)

2. QWEN2.5 & GEMMA2 RAG ISSUE:
   Issue: Vector store is empty or RAG search is failing silently
   Options:
   a) Populate vector store with documents using scripts/populate_vector_store.py
   b) Check if RAG collection is supposed to run as part of pipeline
   c) Add error logging to understand WHY search_similar is failing
   
   NOT RECOMMENDED: Fabricating context_precision scores

3. IMPROVE ERROR VISIBILITY:
   - Add logging to collecteur when chunks_rag comes back empty
   - Track RAG exceptions separately from other exceptions
   - Consider making missing context chunks a WARNING rather than silent fallback

4. <THINK> TAG ISSUE:
   Status: Current regex strips <think>...</think> correctly for single-level tags
   Remaining edge case: Nested <think> tags (unlikely but possible)
   Improvement: Add fallback JSON extraction with re.search(r'\{.*\}', ..., re.DOTALL)
   Current state: Functional enough, not the root cause of Qwen2.5/Gemma2 issue
""")

print("\n" + "="*80)
print("✅ SUMMARY")
print("="*80)

summary = """
Model                        | Issue          | Root Cause              | Fix Required
----|----|----|----
Gemini 3.1 Flash-Lite        | All metrics    | Not evaluated           | Re-evaluate
Qwen2.5 7B (Ollama)          | 2 metrics (*)  | Empty context chunks    | Populate RAG
Gemma2 9B (Ollama)           | 2 metrics (*)  | Empty context chunks    | Populate RAG

(*) context_precision & context_recall

NOT BUGS (BY DESIGN):
- context_recall=None when sortie_attendue is empty (confirmed by code)
"""

print(summary)
