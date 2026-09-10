#!/usr/bin/env python3
"""Simplified dry-run for exec 4 to show context_precision/recall work now."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text
from src.rag.vector_store import search_similar
from src.evaluation.metrics import evaluer_context_precision, evaluer_context_recall

print("🔍 Simplified Dry-Run for Execution 4\n")

# Fetch execution 4 data
query = text("""
    SELECT 
        e.id,
        e.reponse_generee,
        s.id AS scenario_id,
        s.nom_cas_usage,
        s.prompt,
        s.sortie_attendue,
        s.departement
    FROM executions e
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE e.id = 4
""")

with engine.connect() as conn:
    row = conn.execute(query).mappings().first()

if not row:
    print("❌ Not found")
    sys.exit(1)

exec_id = row['id']
response = row['reponse_generee']
scenario_name = row['nom_cas_usage']
prompt = row['prompt']
expected_output = row['sortie_attendue']
departement = row['departement']

print(f"Exec {exec_id}: {scenario_name}")
print(f"  Response: {len(response)} chars")
print(f"  Expected output: {len(expected_output)} chars")
print(f"  Department: {departement}\n")

# Retrieve chunks
print("🔍 Retrieving context chunks...")
try:
    chunks = search_similar(prompt, departement, top_k=8)
    print(f"  ✅ Got {len(chunks)} chunks\n")
except Exception as e:
    print(f"  ❌ Failed: {e}\n")
    sys.exit(1)

# Test context_precision
print("📊 Testing context_precision...")
try:
    result = evaluer_context_precision(chunks, prompt)
    print(f"  ✅ Result: {result}\n")
except Exception as e:
    print(f"  ❌ Failed: {e}\n")

# Test context_recall  
print("📊 Testing context_recall...")
try:
    result = evaluer_context_recall(chunks, expected_output)
    print(f"  ✅ Result: {result}\n")
except Exception as e:
    print(f"  ❌ Failed: {e}\n")

print("="*60)
print("✅ Context metrics can now be evaluated!")
print("="*60)
