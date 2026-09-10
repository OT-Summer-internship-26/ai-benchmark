#!/usr/bin/env python3
"""Find executions with missing context_precision/context_recall for Qwen2.5 and Gemma2."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text

print("🔍 Finding executions with missing context metrics...\n")

query = text("""
    SELECT 
        e.id AS exec_id,
        m.nom AS model,
        s.nom_cas_usage AS scenario,
        COUNT(CASE WHEN sc.critere = 'context_precision' THEN 1 END) AS has_precision,
        COUNT(CASE WHEN sc.critere = 'context_recall' THEN 1 END) AS has_recall,
        COUNT(CASE WHEN sc.critere = 'faithfulness' THEN 1 END) AS has_faith,
        COUNT(CASE WHEN sc.critere = 'answer_relevancy' THEN 1 END) AS has_relevancy
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    LEFT JOIN scores sc ON sc.execution_id = e.id
    WHERE m.nom IN ('Qwen2.5 7B', 'Gemma2 9B')
    GROUP BY e.id, m.nom, s.nom_cas_usage
    ORDER BY m.nom, e.id
""")

with engine.connect() as conn:
    results = conn.execute(query).mappings().all()

# Filter to missing context metrics
missing_precision = [r for r in results if r['has_precision'] == 0]
missing_recall = [r for r in results if r['has_recall'] == 0]

print(f"📊 QWEN2.5 7B & GEMMA2 9B - MISSING CONTEXT METRICS\n")

print(f"Missing context_precision: {len(missing_precision)}")
for r in missing_precision:
    print(f"  - Exec {r['exec_id']:3} ({r['model']:15}) | {r['scenario'][:50]}")

print(f"\nMissing context_recall: {len(missing_recall)}")
for r in missing_recall:
    print(f"  - Exec {r['exec_id']:3} ({r['model']:15}) | {r['scenario'][:50]}")

# Get unique exec_ids to diagnose
unique_ids = sorted(set(
    [r['exec_id'] for r in missing_precision] + 
    [r['exec_id'] for r in missing_recall]
))

print(f"\n📋 Total unique execution_ids to diagnose: {len(unique_ids)}")
print(f"IDs: {unique_ids}")

# Save for next step
with open('qwen_gemma_missing_ids.txt', 'w') as f:
    f.write(','.join(map(str, unique_ids)))
    
print(f"\n✅ Saved to qwen_gemma_missing_ids.txt")
