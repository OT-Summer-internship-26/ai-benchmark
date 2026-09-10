#!/usr/bin/env python3
"""
Check if Gemini 3.1 Flash-Lite executions have scores in the database.
Lists execution_ids that need backfilling if no scores exist.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

print("="*80)
print("🔍 CHECKING GEMINI 3.1 FLASH-LITE SCORES")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Find all Gemini 3.1 Flash-Lite model IDs
print("\n1️⃣  Finding Gemini model in database...\n")

model_query = text("""
    SELECT id, nom, fournisseur, version
    FROM modeles
    WHERE nom ILIKE '%Gemini%' OR nom ILIKE '%gemini%'
    ORDER BY id
""")

with engine.connect() as conn:
    gemini_models = conn.execute(model_query).fetchall()

if not gemini_models:
    print("❌ No Gemini models found in database")
    sys.exit(1)

print(f"✅ Found {len(gemini_models)} Gemini model(s):\n")

for model_id, nom, fournisseur, version in gemini_models:
    print(f"   ID: {model_id} | Name: {nom} | Provider: {fournisseur} | Version: {version}")

# Get Gemini execution IDs
print("\n2️⃣  Finding all Gemini executions...\n")

gemini_exec_query = text("""
    SELECT e.id, m.nom, s.nom_cas_usage, s.departement, e.date_execution
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE m.nom ILIKE '%Gemini%' OR m.nom ILIKE '%gemini%'
    ORDER BY e.id DESC
""")

with engine.connect() as conn:
    gemini_execs = conn.execute(gemini_exec_query).fetchall()

if not gemini_execs:
    print("❌ No Gemini executions found")
    sys.exit(1)

print(f"✅ Found {len(gemini_execs)} Gemini execution(s):\n")

gemini_exec_ids = []
for exec_id, model_nom, scenario, dept, exec_date in gemini_execs:
    gemini_exec_ids.append(exec_id)
    print(f"   exec_id={exec_id:3} | {scenario[:35]:35} | {dept[:20]:20} | {exec_date}")

# Check for scores
print(f"\n3️⃣  CHECKING FOR SCORES (execution_id in scores table)...\n")

scores_query = text("""
    SELECT execution_id, COUNT(*) as score_count
    FROM scores
    WHERE execution_id IN ({})
    GROUP BY execution_id
    ORDER BY execution_id DESC
""".format(','.join(str(id) for id in gemini_exec_ids)))

with engine.connect() as conn:
    scores_results = conn.execute(scores_query).fetchall()

scores_dict = {exec_id: count for exec_id, count in scores_results}

if not scores_results:
    print("❌ NO SCORES FOUND for any Gemini execution\n")
    print("   This confirms Gemini executions were NOT evaluated.")
    print("   Expected behavior: lancer_gemini_16.py skips evaluateur step.\n")
    
    with_scores = []
    without_scores = gemini_exec_ids
else:
    print(f"⚠️  Found scores for {len(scores_results)} execution(s):\n")
    
    with_scores = []
    without_scores = []
    
    for exec_id in gemini_exec_ids:
        if exec_id in scores_dict:
            count = scores_dict[exec_id]
            print(f"   ✅ exec_id={exec_id}: {count} scores")
            with_scores.append(exec_id)
        else:
            without_scores.append(exec_id)
    
    if without_scores:
        print(f"\n   ❌ NO SCORES: {len(without_scores)} execution(s)")
        for exec_id in without_scores:
            print(f"      exec_id={exec_id}")

# Verify which metrics are missing
print(f"\n4️⃣  VERIFYING METRIC COVERAGE...\n")

metric_query = text("""
    SELECT 
        e.id AS execution_id,
        COUNT(DISTINCT sc.critere) as metric_count,
        STRING_AGG(DISTINCT sc.critere, ', ' ORDER BY sc.critere) as metrics
    FROM executions e
    LEFT JOIN scores sc ON sc.execution_id = e.id
    WHERE e.id IN ({})
    GROUP BY e.id
    ORDER BY e.id
""".format(','.join(str(id) for id in gemini_exec_ids)))

with engine.connect() as conn:
    metric_results = conn.execute(metric_query).fetchall()

print("Execution ID | Metrics Present | Status")
print("-" * 70)

all_missing = True
for exec_id, metric_count, metrics in metric_results:
    if metric_count == 0:
        print(f"  {exec_id:12} | NONE            | ❌ Not evaluated")
    else:
        print(f"  {exec_id:12} | {metric_count} metrics | ⚠️  Partially scored")
        all_missing = False

# Final summary
print("\n" + "="*80)
print("📋 SUMMARY")
print("="*80)

print(f"\nTotal Gemini executions: {len(gemini_execs)}")
print(f"With scores: {len(with_scores)}")
print(f"Without scores: {len(without_scores)}")

if all_missing and len(gemini_execs) > 0:
    print(f"\n✅ CONFIRMED: All {len(gemini_execs)} Gemini executions were NOT evaluated")
    print("   This is expected (lancer_gemini_16.py explicitly skips evaluateur)")
    print("\n🔧 EXECUTION IDs NEEDING BACKFILL:")
    print(f"   {without_scores}")
    print(f"\n📝 To backfill, use:")
    print(f"   python scripts/re_evaluate_executions.py --ids {','.join(map(str, without_scores))} --dry-run")
    print(f"   python scripts/re_evaluate_executions.py --ids {','.join(map(str, without_scores))} --apply")
else:
    print(f"\n⚠️  UNEXPECTED: Some Gemini executions have scores")
    print(f"   This suggests evaluateur WAS run for these executions")

# Show breakdown by model
print(f"\n" + "="*80)
print("BREAKDOWN BY MODEL")
print("="*80)

for model_id, nom, fournisseur, version in gemini_models:
    model_execs = [e for e in gemini_execs if e[1] == nom]
    model_with_scores = [e[0] for e in model_execs if e[0] in with_scores]
    
    print(f"\n{nom}:")
    print(f"  Total executions: {len(model_execs)}")
    print(f"  With scores: {len(model_with_scores)}")
    print(f"  Without scores: {len(model_execs) - len(model_with_scores)}")
