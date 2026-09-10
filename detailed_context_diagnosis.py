#!/usr/bin/env python3
"""Detailed diagnosis: check chunks_rag, sortie_attendue, and judge responses."""

import sys
sys.path.insert(0, '.')

from src.database.connection import engine
from sqlalchemy import text
from src.rag.vector_store import search_similar

print("🔬 DETAILED DIAGNOSIS - Context Metrics Missing\n")

# Read the missing metrics details
missing = []
with open('missing_context_details.txt', 'r') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) == 4:
            missing.append({
                'exec_id': int(parts[0]),
                'model': parts[1],
                'metric': parts[2],
                'scenario_id': int(parts[3])
            })

print(f"Analyzing {len(set(m['exec_id'] for m in missing))} executions with {len(missing)} missing metrics\n")

# Group by execution
from itertools import groupby
missing_sorted = sorted(missing, key=lambda x: x['exec_id'])

diagnosis_results = []

with engine.connect() as conn:
    for exec_id, group in groupby(missing_sorted, key=lambda x: x['exec_id']):
        group_list = list(group)
        
        # Fetch execution data
        exec_data = conn.execute(text("""
            SELECT 
                e.id,
                e.scenario_id,
                e.reponse_generee,
                m.nom AS model,
                s.nom_cas_usage,
                s.prompt,
                s.sortie_attendue,
                s.departement
            FROM executions e
            JOIN modeles m ON m.id = e.modele_id
            JOIN scenarios s ON s.id = e.scenario_id
            WHERE e.id = :exec_id
        """), {"exec_id": exec_id}).mappings().first()
        
        if not exec_data:
            print(f"❌ Exec {exec_id}: Not found in database")
            continue
        
        print(f"📍 Execution {exec_id} ({exec_data['model']})")
        print(f"   Scenario: {exec_data['nom_cas_usage']}")
        print(f"   Response length: {len(exec_data['reponse_generee'] or '')}")
        
        # Check sortie_attendue
        sortie = exec_data['sortie_attendue']
        if not sortie or len(sortie.strip()) == 0:
            print(f"   ⚠️  sortie_attendue: EMPTY (context_recall=None is EXPECTED)")
            sortie_status = "EMPTY"
        else:
            print(f"   ✅ sortie_attendue: {len(sortie)} chars")
            sortie_status = "PRESENT"
        
        # Check chunks_rag via search_similar
        try:
            chunks = search_similar(
                query=exec_data['prompt'] or '',
                departement=exec_data['departement'] or '',
                top_k=8
            )
            if not chunks or len(chunks) == 0:
                print(f"   ⚠️  chunks_rag: EMPTY (0 chunks from RAG search)")
                chunks_status = "EMPTY"
            else:
                print(f"   ✅ chunks_rag: {len(chunks)} chunks retrieved")
                chunks_status = "OK"
        except Exception as e:
            print(f"   ❌ chunks_rag: RAG search error - {type(e).__name__}: {str(e)[:50]}")
            chunks_status = "ERROR"
            chunks = []
        
        # For each missing metric, record diagnosis
        for item in group_list:
            metric = item['metric']
            
            if metric == 'context_recall' and sortie_status == "EMPTY":
                root_cause = "empty_sortie_attendue_expected"
            elif chunks_status == "EMPTY":
                root_cause = "empty_chunks_rag"
            elif chunks_status == "ERROR":
                root_cause = "rag_search_error"
            else:
                # Both chunks and sortie look OK, so judge must be failing
                root_cause = "judge_unknown"
            
            diagnosis_results.append({
                'exec_id': exec_id,
                'model': exec_data['model'],
                'scenario_id': exec_data['scenario_id'],
                'scenario': exec_data['nom_cas_usage'],
                'metric': metric,
                'sortie_status': sortie_status,
                'chunks_status': chunks_status,
                'root_cause': root_cause,
                'chunks_count': len(chunks),
                'response_len': len(exec_data['reponse_generee'] or ''),
                'prompt': exec_data['prompt'],
                'reponse': exec_data['reponse_generee'],
                'chunks': chunks,
                'sortie': sortie
            })
        
        print()

# Print summary table
print("\n" + "="*120)
print("📊 DIAGNOSIS SUMMARY TABLE\n")

print(f"{'Exec ID':8} | {'Model':20} | {'Metric':18} | {'Sortie':12} | {'Chunks':12} | {'Root Cause':35}")
print("-" * 120)

for d in diagnosis_results:
    exec_id = d['exec_id']
    model = d['model'][:20]
    metric = d['metric'][:18]
    sortie = d['sortie_status'][:12]
    chunks = f"{d['chunks_count']} chunks" if d['chunks_status'] == 'OK' else d['chunks_status'][:12]
    root = d['root_cause'][:35]
    
    print(f"{exec_id:8} | {model:20} | {metric:18} | {sortie:12} | {chunks:12} | {root:35}")

# Save for next step (judge testing)
import json
with open('diagnosis_results.json', 'w') as f:
    # Convert to serializable format
    to_save = []
    for d in diagnosis_results:
        to_save.append({
            'exec_id': d['exec_id'],
            'model': d['model'],
            'metric': d['metric'],
            'scenario': d['scenario'],
            'root_cause': d['root_cause'],
            'sortie_status': d['sortie_status'],
            'chunks_status': d['chunks_status'],
            'chunks_count': d['chunks_count'],
            'response_len': d['response_len']
        })
    json.dump(to_save, f, indent=2)

print(f"\n✅ Saved detailed results to diagnosis_results.json")
