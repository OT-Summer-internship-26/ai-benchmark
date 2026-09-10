#!/usr/bin/env python3
"""Diagnose context_precision/recall missing for Qwen2.5 7B and Gemma2 9B."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text

print("🔍 DIAGNOSING QWEN2.5 7B (OLLAMA) & GEMMA2 9B\n")

# Find all executions with scores for these models
query = text("""
    SELECT 
        e.id,
        m.nom AS model,
        s.id AS scenario_id,
        s.nom_cas_usage,
        COUNT(CASE WHEN sc.critere = 'context_precision' THEN 1 END) AS has_precision,
        COUNT(CASE WHEN sc.critere = 'context_recall' THEN 1 END) AS has_recall,
        COUNT(CASE WHEN sc.critere = 'faithfulness' THEN 1 END) AS has_faith,
        COUNT(CASE WHEN sc.critere = 'answer_relevancy' THEN 1 END) AS has_relevancy
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    LEFT JOIN scores sc ON sc.execution_id = e.id
    WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B')
    GROUP BY e.id, m.nom, s.id, s.nom_cas_usage
    ORDER BY m.nom, e.id
""")

with engine.connect() as conn:
    results = conn.execute(query).mappings().all()

print(f"Found {len(results)} executions\n")

# Identify missing context metrics
missing_metrics = []

for r in results:
    exec_id = r['id']
    model = r['model']
    scenario_id = r['scenario_id']
    scenario_name = r['nom_cas_usage']
    
    if r['has_precision'] == 0:
        missing_metrics.append({
            'exec_id': exec_id,
            'model': model,
            'metric': 'context_precision',
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'other_metrics': f"faith={r['has_faith']}, relevancy={r['has_relevancy']}, recall={r['has_recall']}"
        })
    
    if r['has_recall'] == 0:
        missing_metrics.append({
            'exec_id': exec_id,
            'model': model,
            'metric': 'context_recall',
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'other_metrics': f"faith={r['has_faith']}, relevancy={r['has_relevancy']}, precision={r['has_precision']}"
        })

print(f"📋 Missing context metrics: {len(missing_metrics)}\n")

if missing_metrics:
    print(f"{'Exec ID':8} | {'Model':20} | {'Metric':18} | {'Scenario':40} | {'Others'}")
    print("-" * 110)
    
    for m in missing_metrics:
        exec_id = m['exec_id']
        model = m['model'][:20]
        metric = m['metric'][:18]
        scenario = m['scenario_name'][:40]
        others = m['other_metrics']
        print(f"{exec_id:8} | {model:20} | {metric:18} | {scenario:40} | {others}")
    
    # Save for detailed analysis
    with open('missing_context_details.txt', 'w') as f:
        for m in missing_metrics:
            f.write(f"{m['exec_id']}|{m['model']}|{m['metric']}|{m['scenario_id']}\n")
    
    print(f"\n✅ Saved details to missing_context_details.txt")
else:
    print("✅ No missing context metrics found for these models!")
