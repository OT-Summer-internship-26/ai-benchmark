#!/usr/bin/env python3
"""Test context_precision on execution_id 4 with the new max_tokens=2500 fix."""

import sys
sys.path.insert(0, '.')

import os
import warnings
import httpx
import certifi
import json

warnings.filterwarnings('ignore')

# Setup SSL
os.environ['SSL_CERT_FILE'] = certifi.where()

_original_httpx_client_init = httpx.Client.__init__

def _patched_httpx_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_httpx_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_httpx_client_init

# Import after SSL setup
from src.database.connection import engine
from src.rag.vector_store import search_similar
from src.evaluation.metrics import evaluer_context_precision, evaluer_context_recall
from sqlalchemy import text

print("=" * 100)
print("TEST: context_precision + context_recall on execution_id 4 with max_tokens=2500")
print("=" * 100)

# Get execution 4 data
with engine.connect() as conn:
    # Fetch execution
    exec_row = conn.execute(text("""
        SELECT e.id, e.scenario_id, e.reponse_generee as reponse, e.modele_id,
               m.nom as modele_nom
        FROM executions e JOIN modeles m ON m.id=e.modele_id
        WHERE e.id = :eid
    """), {"eid": 4}).mappings().first()
    
    if not exec_row:
        print("❌ No execution with id 4 found!")
        sys.exit(1)
    
    # Fetch scenario
    scenario_row = conn.execute(text("""
        SELECT id, nom_cas_usage, prompt, sortie_attendue, departement
        FROM scenarios WHERE id = :sid
    """), {"sid": exec_row["scenario_id"]}).mappings().first()
    
    if not scenario_row:
        print("❌ Scenario not found for this execution!")
        sys.exit(1)

scenario_dict = dict(scenario_row)

# Compute chunks via vector store
try:
    chunks_rag = search_similar(
        query=scenario_dict.get("prompt", ""), 
        departement=scenario_dict.get("departement", ""), 
        top_k=8
    )
except Exception as e:
    print(f"⚠️  Warning: search_similar failed: {e}")
    chunks_rag = []

print(f"\n📋 Execution Data:")
print(f"   execution_id: {exec_row['id']}")
print(f"   scenario_id: {exec_row['scenario_id']}")
print(f"   model: {exec_row['modele_nom']}")
print(f"   question: {scenario_dict.get('prompt', '')[:100]}...")
print(f"   chunks_rag count: {len(chunks_rag)}")

if chunks_rag:
    print(f"   First chunk preview: {chunks_rag[0][:100]}...")

sortie_attendue = scenario_dict.get("sortie_attendue")
print(f"   sortie_attendue: {sortie_attendue[:100] if sortie_attendue else 'None'}...")

if not chunks_rag:
    print("\n⚠️  WARNING: chunks_rag is empty! context_precision/recall will be evaluated on empty context.")

print("\n" + "=" * 100)
print("TEST 1: evaluer_context_precision(chunks_rag, question)")
print("=" * 100)

question = scenario_dict.get("prompt", "")

try:
    result_precision = evaluer_context_precision(chunks_rag, question)
    
    print(f"\n✅ SUCCESS!")
    print(f"   Result: {result_precision}")
    
    if result_precision.get("note") is not None:
        print(f"\n   ✅ JSON parsed successfully!")
        print(f"   Note: {result_precision['note']}")
        print(f"   Justification: {result_precision['justification']}")
    else:
        print(f"\n   ⚠️  Note is None (evaluation failed)")
        print(f"   Justification: {result_precision['justification']}")
        
except Exception as e:
    print(f"\n❌ FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
print("TEST 2: evaluer_context_recall(chunks_rag, sortie_attendue)")
print("=" * 100)

if not sortie_attendue:
    print("\n⚠️  SKIPPED: sortie_attendue is empty (context_recall returns None by design)")
else:
    try:
        result_recall = evaluer_context_recall(chunks_rag, sortie_attendue)
        
        print(f"\n✅ SUCCESS!")
        print(f"   Result: {result_recall}")
        
        if result_recall.get("note") is not None:
            print(f"\n   ✅ JSON parsed successfully!")
            print(f"   Note: {result_recall['note']}")
            print(f"   Justification: {result_recall['justification']}")
        else:
            print(f"\n   ⚠️  Note is None (evaluation failed)")
            print(f"   Justification: {result_recall['justification']}")
            
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print("\n✅ Test completed - check results above\n")
