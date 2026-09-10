#!/usr/bin/env python3
"""Verify Gemini backfill was successful."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text

print("📊 Gemini 3.1 Flash-Lite Score Verification\n")

with engine.connect() as conn:
    # Get summary
    summary = conn.execute(text('''
        SELECT 
            COUNT(DISTINCT e.id) AS executions,
            COUNT(*) AS total_scores,
            COUNT(DISTINCT sc.critere) AS unique_metrics
        FROM executions e
        LEFT JOIN scores sc ON sc.execution_id = e.id
        WHERE e.id IN (74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89)
    ''')).mappings().first()
    
    print(f"Summary:")
    print(f"  Executions: {summary['executions']}/16")
    print(f"  Total scores: {summary['total_scores']}")
    print(f"  Unique metrics: {summary['unique_metrics']}\n")
    
    # Get per-execution breakdown
    details = conn.execute(text('''
        SELECT 
            e.id AS exec_id,
            COUNT(*) AS score_count,
            CAST(AVG(CAST(sc.note AS FLOAT)) AS NUMERIC(10,3)) AS avg_note,
            MIN(CAST(sc.note AS FLOAT)) AS min_note,
            MAX(CAST(sc.note AS FLOAT)) AS max_note
        FROM executions e
        LEFT JOIN scores sc ON sc.execution_id = e.id
        WHERE e.id IN (74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89)
        GROUP BY e.id
        ORDER BY e.id
    ''')).mappings().all()
    
    print(f"Detailed Scores:\n")
    print(f"{'Exec ID':8} | {'Scores':8} | {'Avg Note':10} | {'Min':6} | {'Max':6}")
    print("-" * 60)
    
    for row in details:
        exec_id = row['exec_id']
        score_count = row['score_count']
        avg_note = row['avg_note'] if row['avg_note'] else 'N/A'
        min_note = f"{row['min_note']:.3f}" if row['min_note'] else 'N/A'
        max_note = f"{row['max_note']:.3f}" if row['max_note'] else 'N/A'
        print(f"{exec_id:8} | {score_count:8} | {str(avg_note):10} | {min_note:6} | {max_note:6}")
    
    # Check for any remaining None values
    print(f"\n\nMetrics Breakdown:")
    metrics_check = conn.execute(text('''
        SELECT 
            sc.critere,
            COUNT(*) AS count,
            COUNT(CASE WHEN sc.note IS NULL THEN 1 END) AS null_count
        FROM scores sc
        WHERE sc.execution_id IN (74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89)
        GROUP BY sc.critere
        ORDER BY sc.critere
    ''')).mappings().all()
    
    for row in metrics_check:
        critere = row['critere']
        count = row['count']
        null_count = row['null_count']
        status = "✅" if null_count == 0 else "⚠️"
        print(f"  {status} {critere:20} : {count:3} rows, {null_count} nulls")

print("\n" + "="*60)
if summary['executions'] == 16 and summary['total_scores'] == 80:
    print("✅✅✅ BACKFILL SUCCESSFUL!")
    print(f"All 16 executions have scores")
else:
    print("⚠️ PARTIAL BACKFILL")
    print(f"Expected: 16 executions, 80 scores")
    print(f"Got: {summary['executions']} executions, {summary['total_scores']} scores")
print("="*60)
