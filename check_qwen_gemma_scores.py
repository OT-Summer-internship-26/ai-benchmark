#!/usr/bin/env python3
"""Check all scores for Qwen2.5 and Gemma2 models."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text

print("📊 Checking all scores for Qwen2.5 7B and Gemma2 9B\n")

query = text("""
    SELECT 
        e.id,
        m.nom AS model,
        COUNT(*) AS total_scores,
        COUNT(CASE WHEN sc.critere = 'faithfulness' AND sc.note IS NOT NULL THEN 1 END) AS faith_count,
        COUNT(CASE WHEN sc.critere = 'answer_relevancy' AND sc.note IS NOT NULL THEN 1 END) AS relevancy_count,
        COUNT(CASE WHEN sc.critere = 'context_precision' AND sc.note IS NOT NULL THEN 1 END) AS precision_count,
        COUNT(CASE WHEN sc.critere = 'context_recall' AND sc.note IS NOT NULL THEN 1 END) AS recall_count
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN scores sc ON sc.execution_id = e.id
    WHERE m.nom IN ('Qwen2.5 7B', 'Gemma2 9B')
    GROUP BY e.id, m.nom
    ORDER BY m.nom, e.id
""")

with engine.connect() as conn:
    results = conn.execute(query).mappings().all()

print(f"{'Exec ID':8} | {'Model':15} | {'Total':6} | {'Faith':6} | {'Relevancy':10} | {'Precision':10} | {'Recall':7}")
print("-" * 90)

for r in results:
    exec_id = r['id']
    model = r['model'][:15]
    total = r['total_scores']
    faith = r['faith_count']
    relevancy = r['relevancy_count']
    precision = r['precision_count']
    recall = r['recall_count']
    
    print(f"{exec_id:8} | {model:15} | {total:6} | {faith:6} | {relevancy:10} | {precision:10} | {recall:7}")

# Summary
print("\n" + "="*90)
qwen_results = [r for r in results if r['model'] == 'Qwen2.5 7B']
gemma_results = [r for r in results if r['model'] == 'Gemma2 9B']

print(f"\nQwen2.5 7B: {len(qwen_results)} executions")
print(f"  - Avg total scores: {sum(r['total_scores'] for r in qwen_results) / len(qwen_results) if qwen_results else 0:.1f}")

print(f"\nGemma2 9B: {len(gemma_results)} executions")
print(f"  - Avg total scores: {sum(r['total_scores'] for r in gemma_results) / len(gemma_results) if gemma_results else 0:.1f}")
