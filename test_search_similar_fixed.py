#!/usr/bin/env python3
"""Test search_similar() for one of the affected executions (exec_id=4)."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text
from src.rag.vector_store import search_similar

print("🔍 Testing search_similar() with affected execution\n")

# Get scenario for execution 4
query = text("""
    SELECT 
        e.id,
        s.id AS scenario_id,
        s.nom_cas_usage,
        s.prompt,
        s.departement
    FROM executions e
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE e.id = 4
""")

with engine.connect() as conn:
    row = conn.execute(query).mappings().first()

if not row:
    print("❌ Execution 4 not found")
    sys.exit(1)

exec_id = row['id']
scenario_id = row['scenario_id']
scenario_name = row['nom_cas_usage']
prompt = row['prompt']
departement = row['departement']

print(f"📍 Execution ID: {exec_id}")
print(f"   Scenario ID: {scenario_id}")
print(f"   Scenario: {scenario_name}")
print(f"   Department: {departement}")
print(f"   Prompt: {prompt[:100]}...\n")

try:
    print("🔍 Calling search_similar()...")
    chunks = search_similar(
        query=prompt,
        departement=departement,
        top_k=8
    )
    
    print(f"\n✅ SUCCESS! Retrieved {len(chunks)} chunks\n")
    
    if len(chunks) > 0:
        print("📊 Chunks retrieved:")
        for i, chunk in enumerate(chunks, 1):
            preview = chunk[:100].replace('\n', ' ')
            print(f"\n   Chunk {i}:")
            print(f"   {preview}...")
            if len(chunk) > 100:
                print(f"   [Total length: {len(chunk)} chars]")
    else:
        print("⚠️  No chunks retrieved (empty result)")
    
    print("\n" + "="*60)
    print("✅ search_similar() is working!")
    print("="*60)
    
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
