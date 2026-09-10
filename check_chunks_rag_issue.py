#!/usr/bin/env python3
"""
Check if chunks_rag is properly populated for scenarios used by Qwen2.5 and Gemma2.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

# Get the scenarios used by Qwen2.5 and Gemma2
query = text("""
    SELECT DISTINCT
        s.id,
        s.nom_cas_usage,
        s.departement,
        s.prompt,
        LENGTH(COALESCE(s.prompt, '')) AS prompt_len,
        s.sortie_attendue,
        LENGTH(COALESCE(s.sortie_attendue, '')) AS sortie_len
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B (Ollama)')
    ORDER BY s.id
""")

with engine.connect() as conn:
    results = conn.execute(query).fetchall()

print("🔍 SCENARIOS USED BY QWEN2.5 & GEMMA2:\n")
print("Scenario ID | Name | Dept | Prompt Len | Sortie Len")
print("-" * 70)

for scenario_id, name, dept, prompt, prompt_len, sortie_attendue, sortie_len in results:
    print(f"{scenario_id:11} | {name[:20]:20} | {dept[:15]:15} | {prompt_len:10} | {sortie_len:10}")

print("\n" + "="*70)
print("ℹ️  NOTE: The scenarios table does NOT have a 'chunks_rag' column.")
print("   chunks_rag is expected to come from the LangGraph state during pipeline execution.")
print("   If chunks_rag is empty [], then context_precision returns None (judge cannot evaluate empty context).")
print("\n🔧 NEXT STEP: Check the collecteur agent to see if it's populating chunks_rag properly.")

# Check if there's RAG/chunks functionality
print("\n" + "="*70)
print("🔍 CHECKING FOR RAG DATA IN PIPELINE:\n")

try:
    from src.agents import collecteur
    import inspect
    
    # Check the collecteur source
    source = inspect.getsource(collecteur.run_collecteur)
    if "chunks" in source or "rag" in source.lower():
        print("✅ Found RAG/chunks references in collecteur")
        # Print relevant lines
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'chunks' in line.lower() or 'rag' in line.lower():
                print(f"   Line {i}: {line.strip()[:80]}")
    else:
        print("❌ No RAG/chunks references found in collecteur")
        print("   This might be why context_precision is failing - no context data provided!")
        
except Exception as e:
    print(f"⚠️  Could not inspect collecteur: {e}")
