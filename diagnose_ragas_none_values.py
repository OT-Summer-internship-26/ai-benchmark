#!/usr/bin/env python3
"""
Diagnostic script to investigate None values in RAGAS scores.
Focuses on:
1. Gemini 3.1 Flash-Lite (ALL metrics None)
2. Qwen2.5 7B (context_precision/recall None)
3. Gemma2 9B (context_precision/recall None)
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

def diagnose_gemini_executions():
    """Check if Gemini executions have any scores at all."""
    print("\n" + "="*70)
    print("1️⃣  GEMINI 3.1 FLASH-LITE DIAGNOSIS")
    print("="*70)
    
    query = text("""
        SELECT 
            e.id AS execution_id,
            m.nom AS model_name,
            s.nom_cas_usage AS scenario_name,
            COUNT(sc.id) AS score_count
        FROM executions e
        JOIN modeles m ON m.id = e.modele_id
        JOIN scenarios s ON s.id = e.scenario_id
        LEFT JOIN scores sc ON sc.execution_id = e.id
        WHERE m.nom LIKE '%Gemini%' OR m.nom LIKE '%gemini%'
        GROUP BY e.id, m.nom, s.nom_cas_usage
        ORDER BY e.id DESC
        LIMIT 20
    """)
    
    with engine.connect() as conn:
        results = conn.execute(query).fetchall()
    
    if not results:
        print("❌ No Gemini executions found in database")
        return []
    
    print(f"\n✅ Found {len(results)} Gemini execution(s):\n")
    gemini_exec_ids = []
    
    for execution_id, model_name, scenario_name, score_count in results:
        status = "✅ Scored" if score_count > 0 else "❌ NO SCORES"
        print(f"  execution_id={execution_id} | {model_name} | {scenario_name[:40]} | {status} ({score_count} scores)")
        gemini_exec_ids.append(execution_id)
    
    # Check if ANY Gemini execution has scores
    unscored_gemini = [exec_id for exec_id, model, scenario, count in results if count == 0]
    
    if unscored_gemini:
        print(f"\n🔍 Result: Gemini executions have NO scores in database (as expected from lancer_gemini_16.py)")
        print(f"   These execution_ids need re-evaluation: {unscored_gemini}")
        return unscored_gemini
    else:
        print(f"\n✅ Gemini executions have scores - no backfill needed")
        return []

def diagnose_qwen_and_gemma():
    """Diagnose why Qwen2.5 and Gemma2 have None for context metrics."""
    print("\n" + "="*70)
    print("2️⃣  QWEN2.5 7B & GEMMA2 9B CONTEXT METRICS DIAGNOSIS")
    print("="*70)
    
    # First, get executions for these models
    query = text("""
        SELECT DISTINCT
            e.id AS execution_id,
            m.nom AS model_name,
            s.id AS scenario_id,
            s.nom_cas_usage AS scenario_name,
            s.sortie_attendue,
            LENGTH(COALESCE(s.sortie_attendue, '')) AS sortie_length
        FROM executions e
        JOIN modeles m ON m.id = e.modele_id
        JOIN scenarios s ON s.id = e.scenario_id
        WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B (Ollama)')
        ORDER BY m.nom, e.id DESC
        LIMIT 30
    """)
    
    with engine.connect() as conn:
        exec_results = conn.execute(query).fetchall()
    
    if not exec_results:
        print("❌ No Qwen2.5 or Gemma2 executions found")
        return {}
    
    print(f"\n✅ Found {len(exec_results)} executions for Qwen2.5/Gemma2\n")
    
    # Group by model
    by_model = {}
    for execution_id, model_name, scenario_id, scenario_name, sortie_attendue, sortie_length in exec_results:
        if model_name not in by_model:
            by_model[model_name] = []
        by_model[model_name].append({
            'execution_id': execution_id,
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'sortie_attendue': sortie_attendue,
            'sortie_length': sortie_length
        })
    
    diagnosis = {}
    
    for model_name, execs in by_model.items():
        print(f"\n📊 Model: {model_name}")
        print(f"   Total executions: {len(execs)}")
        
        # Check sortie_attendue population
        with_sortie = sum(1 for e in execs if e['sortie_length'] > 0)
        without_sortie = len(execs) - with_sortie
        
        print(f"   - With sortie_attendue: {with_sortie}")
        print(f"   - Without sortie_attendue: {without_sortie}")
        
        if without_sortie > 0:
            print(f"   ⚠️  {without_sortie} scenarios missing sortie_attendue (context_recall will be None by design)")
            scenario_ids = [e['scenario_id'] for e in execs if e['sortie_length'] == 0]
            print(f"       Scenario IDs: {scenario_ids}")
        
        # Check for context_precision/recall scores
        for exec_data in execs[:5]:  # Check first 5
            exec_id = exec_data['execution_id']
            score_query = text("""
                SELECT critere, note FROM scores 
                WHERE execution_id = :exec_id
                AND critere IN ('context_precision', 'context_recall', 'faithfulness', 'answer_relevancy')
                ORDER BY critere
            """)
            
            with engine.connect() as conn:
                scores = conn.execute(score_query, {'exec_id': exec_id}).fetchall()
            
            score_dict = {critere: note for critere, note in scores}
            precision = score_dict.get('context_precision', 'NOT IN DB')
            recall = score_dict.get('context_recall', 'NOT IN DB')
            
            if precision is None or recall is None:
                print(f"   - exec_id={exec_id}: precision={precision}, recall={recall}")
        
        diagnosis[model_name] = {
            'total_execs': len(execs),
            'with_sortie': with_sortie,
            'without_sortie': without_sortie,
            'scenario_ids_no_sortie': [e['scenario_id'] for e in execs if e['sortie_length'] == 0]
        }
    
    return diagnosis

def check_metrics_py_parsing():
    """Check if the <think> tag stripping is working correctly."""
    print("\n" + "="*70)
    print("3️⃣  CHECKING METRICS.PY JSON PARSING")
    print("="*70)
    
    try:
        from src.evaluation.metrics import _appeler_juge_une_fois
        import inspect
        
        source = inspect.getsource(_appeler_juge_une_fois)
        
        # Check for <think> tag handling
        if "<think>" in source or "re.sub" in source:
            print("✅ Found <think> tag handling in _appeler_juge_une_fois()")
            
            # Extract the relevant lines
            lines = source.split('\n')
            for i, line in enumerate(lines):
                if 'think' in line.lower() or 're.sub' in line:
                    print(f"   Line {i}: {line.strip()}")
        else:
            print("⚠️  No <think> tag handling found in current code")
        
        # Check for JSON extraction fallback
        if 're.search' in source and r'\{.*\}' in source:
            print("✅ Found JSON regex fallback pattern")
        else:
            print("⚠️  No JSON extraction fallback pattern found")
            
    except Exception as e:
        print(f"❌ Error checking metrics.py: {e}")

def check_raw_judge_responses():
    """Check if there are any error logs from judge calls."""
    print("\n" + "="*70)
    print("4️⃣  CHECKING FOR JUDGE CALL ERRORS IN LOGS")
    print("="*70)
    
    log_file = "logs/benchmark.log"
    if not os.path.exists(log_file):
        print("⚠️  No log file found")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.read()
        
        # Look for judge-related errors
        error_indicators = [
            'Groq',
            'juge',
            'JSON',
            'parse',
            '<think>',
            'context_precision',
            'context_recall'
        ]
        
        error_lines = []
        for line in logs.split('\n'):
            if any(indicator in line for indicator in error_indicators) and ('ERROR' in line or 'error' in line):
                error_lines.append(line)
        
        if error_lines:
            print(f"\n✅ Found {len(error_lines)} relevant error lines in logs:")
            for line in error_lines[-10:]:  # Last 10
                print(f"   {line[:120]}")
        else:
            print("ℹ️  No judge-related errors found in recent logs")
            
    except Exception as e:
        print(f"❌ Error reading logs: {e}")

def main():
    print("🔍 RAGAS SCORES NONE VALUES DIAGNOSTIC")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run diagnostics
    gemini_unscored = diagnose_gemini_executions()
    qwen_gemma_diagnosis = diagnose_qwen_and_gemma()
    check_metrics_py_parsing()
    check_raw_judge_responses()
    
    # Summary
    print("\n" + "="*70)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*70)
    
    print(f"\n1. GEMINI 3.1 FLASH-LITE:")
    if gemini_unscored:
        print(f"   ✅ Confirmed: NO scores in database (expected from lancer_gemini_16.py)")
        print(f"   📝 Execution IDs needing re-evaluation: {gemini_unscored}")
    else:
        print(f"   ℹ️  Has scores or no executions found")
    
    print(f"\n2. QWEN2.5 7B & GEMMA2 9B:")
    for model, data in qwen_gemma_diagnosis.items():
        print(f"   {model}:")
        print(f"     - Total: {data['total_execs']} executions")
        print(f"     - With sortie_attendue: {data['with_sortie']}")
        print(f"     - Without sortie_attendue: {data['without_sortie']} (context_recall will be None by design)")
        if data['scenario_ids_no_sortie']:
            print(f"     - Scenario IDs without sortie: {data['scenario_ids_no_sortie']}")
    
    print(f"\n3. METRICS.PY PARSING:")
    print(f"   Review code section above for current JSON parsing strategy")

if __name__ == "__main__":
    main()
