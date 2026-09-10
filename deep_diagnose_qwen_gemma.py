#!/usr/bin/env python3
"""
Deep diagnostic for Qwen2.5 and Gemma2 context_precision/recall issues.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

def deep_diagnose():
    print("🔍 DEEP DIAGNOSTIC: Qwen2.5 & Gemma2 Context Metrics\n")
    
    # Get all Qwen2.5 and Gemma2 executions with their scores
    query = text("""
        SELECT 
            e.id AS execution_id,
            m.nom AS model_name,
            s.nom_cas_usage AS scenario_name,
            STRING_AGG(
                CONCAT(sc.critere, '=', COALESCE(sc.note::TEXT, 'NULL')), 
                ' | ' 
                ORDER BY sc.critere
            ) AS all_scores
        FROM executions e
        JOIN modeles m ON m.id = e.modele_id
        JOIN scenarios s ON s.id = e.scenario_id
        LEFT JOIN scores sc ON sc.execution_id = e.id
        WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B (Ollama)')
        GROUP BY e.id, m.nom, s.nom_cas_usage
        ORDER BY m.nom, e.id DESC
    """)
    
    with engine.connect() as conn:
        results = conn.execute(query).fetchall()
    
    print(f"Found {len(results)} executions:\n")
    print("execution_id | model_name | scenario | scores")
    print("-" * 120)
    
    summary = {}
    
    for execution_id, model_name, scenario_name, all_scores in results:
        if model_name not in summary:
            summary[model_name] = {'total': 0, 'context_precision_none': 0, 'context_recall_none': 0, 'any_scores': 0}
        
        summary[model_name]['total'] += 1
        
        if all_scores is None or all_scores.strip() == '':
            all_scores = "NO SCORES IN DB"
            summary[model_name]['any_scores'] += 1
        else:
            # Check for specific None values
            if 'context_precision=NULL' in all_scores or 'context_precision' not in all_scores:
                summary[model_name]['context_precision_none'] += 1
            if 'context_recall=NULL' in all_scores or 'context_recall' not in all_scores:
                summary[model_name]['context_recall_none'] += 1
        
        print(f"{execution_id:12} | {model_name:20} | {scenario_name[:30]:30} | {str(all_scores)[:60]}")
    
    print("\n" + "="*120)
    print("SUMMARY BY MODEL:\n")
    
    for model_name, stats in summary.items():
        print(f"{model_name}:")
        print(f"  - Total executions: {stats['total']}")
        print(f"  - With context_precision=NULL: {stats['context_precision_none']}")
        print(f"  - With context_recall=NULL: {stats['context_recall_none']}")
        print(f"  - With NO scores at all: {stats['any_scores']}")
        print()
    
    # Get detailed score breakdown
    print("\n" + "="*120)
    print("DETAILED METRIC BREAKDOWN:\n")
    
    metric_query = text("""
        SELECT 
            m.nom AS model_name,
            sc.critere AS metric,
            COUNT(CASE WHEN sc.note IS NOT NULL THEN 1 END) AS non_null_count,
            COUNT(CASE WHEN sc.note IS NULL THEN 1 END) AS null_count,
            COUNT(*) AS total_count,
            ROUND(AVG(sc.note)::NUMERIC, 3) AS avg_note
        FROM executions e
        JOIN modeles m ON m.id = e.modele_id
        LEFT JOIN scores sc ON sc.execution_id = e.id
        WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B (Ollama)')
        GROUP BY m.nom, sc.critere
        ORDER BY m.nom, sc.critere
    """)
    
    with engine.connect() as conn:
        metric_results = conn.execute(metric_query).fetchall()
    
    print("Model | Metric | Non-Null | Null | Total | Avg")
    print("-" * 70)
    
    for model_name, metric, non_null_count, null_count, total_count, avg_note in metric_results:
        metric_display = metric if metric else "NULL"
        avg_display = f"{avg_note:.3f}" if avg_note else "N/A"
        status = "✅" if null_count == 0 else f"⚠️ {null_count} None"
        print(f"{model_name:20} | {metric_display:18} | {non_null_count:8} | {null_count:4} | {total_count:5} | {avg_display}")

if __name__ == "__main__":
    deep_diagnose()
