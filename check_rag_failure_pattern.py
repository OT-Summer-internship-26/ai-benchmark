#!/usr/bin/env python3
"""Check if RAG failures affected OTHER executions beyond the known 4."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text

print("🔍 Checking for broader RAG failure pattern\n")

# Strategy: Compare execution groups to see which have anomalously low scores
# Successful models should have mostly non-zero/non-None values
# Failed models might show patterns of missing specific metrics

query = text("""
    SELECT 
        m.nom AS model,
        COUNT(DISTINCT e.id) AS total_executions,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_precision' THEN e.id END) AS has_precision,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_recall' THEN e.id END) AS has_recall,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_precision' AND sc.note IS NULL THEN e.id END) AS null_precision,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_recall' AND sc.note IS NULL THEN e.id END) AS null_recall,
        COUNT(DISTINCT CASE WHEN sc.critere = 'faithfulness' THEN e.id END) AS has_faith,
        COUNT(DISTINCT CASE WHEN sc.critere = 'answer_relevancy' THEN e.id END) AS has_relevancy
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN scores sc ON sc.execution_id = e.id
    GROUP BY m.nom
    ORDER BY m.nom
""")

with engine.connect() as conn:
    results = conn.execute(query).mappings().all()

print(f"{'Model':30} | {'Execs':6} | {'Precision':10} | {'Recall':10} | {'Faith':8} | {'Relevancy':10}")
print("-" * 100)

for row in results:
    model = row['model'][:30]
    execs = row['total_executions']
    has_prec = row['has_precision']
    has_rec = row['has_recall']
    null_prec = row['null_precision']
    null_rec = row['null_recall']
    has_faith = row['has_faith']
    has_relev = row['has_relevancy']
    
    # Show both present and null counts
    prec_str = f"{has_prec}/{null_prec}N"
    rec_str = f"{has_rec}/{null_rec}N"
    
    print(f"{model:30} | {execs:6} | {prec_str:10} | {rec_str:10} | {has_faith:8} | {has_relev:10}")

print("\n" + "="*100)
print("Analysis:")
print("="*100)

# Identify patterns
for row in results:
    model = row['model']
    execs = row['total_executions']
    null_prec = row['null_precision']
    null_rec = row['null_recall']
    
    if execs == 0:
        continue
    
    prec_missing_pct = (null_prec / execs * 100) if execs > 0 else 0
    rec_missing_pct = (null_rec / execs * 100) if execs > 0 else 0
    
    if prec_missing_pct > 50 or rec_missing_pct > 50:
        print(f"\n⚠️  {model}")
        print(f"   context_precision missing: {null_prec}/{execs} ({prec_missing_pct:.0f}%)")
        print(f"   context_recall missing: {null_rec}/{execs} ({rec_missing_pct:.0f}%)")
        
        # Check which executions
        exec_query = text(f"""
            SELECT DISTINCT e.id
            FROM executions e
            JOIN modeles m ON m.id = e.modele_id
            LEFT JOIN scores sc ON sc.execution_id = e.id
            WHERE m.nom = :model
            AND (
                NOT EXISTS (SELECT 1 FROM scores WHERE execution_id = e.id AND critere = 'context_precision')
                OR NOT EXISTS (SELECT 1 FROM scores WHERE execution_id = e.id AND critere = 'context_recall')
            )
            ORDER BY e.id
        """)
        
        with engine.connect() as conn:
            problem_execs = conn.execute(exec_query, {"model": model}).fetchall()
            exec_ids = [str(row[0]) for row in problem_execs]
            if exec_ids:
                print(f"   Affected exec_ids: {', '.join(exec_ids)}")

print("\n" + "="*100)
