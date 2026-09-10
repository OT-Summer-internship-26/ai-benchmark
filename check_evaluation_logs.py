#!/usr/bin/env python3
"""
Check evaluation logs for Qwen2.5 and Gemma2 executions.
"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

# Get execution IDs for Qwen2.5 and Gemma2
query = text("""
    SELECT e.id, m.nom, s.nom_cas_usage
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    WHERE m.nom IN ('Qwen2.5 7B (Ollama)', 'Gemma2 9B (Ollama)')
    ORDER BY e.id DESC
""")

with engine.connect() as conn:
    results = conn.execute(query).fetchall()

exec_ids = [str(exec_id) for exec_id, _, _ in results]
print(f"Looking for logs for executions: {exec_ids}\n")

# Check logs
log_file = "logs/benchmark.log"
if not os.path.exists(log_file):
    print("❌ Log file not found")
else:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        logs = f.read()
    
    # Search for entries related to these executions or evaluation failures
    print("🔍 SEARCHING LOGS FOR CONTEXT_PRECISION/RECALL ISSUES:\n")
    
    relevant_patterns = [
        r'context_precision.*None',
        r'context_recall.*None',
        r'Qwen2\.5|Gemma2',
        r'evaluer_context_precision|evaluer_context_recall',
        r'<think>.*?</think>',
        r'JSON.*error|json.loads',
        r'execution_id.{0,50}(4|7|8|11|12|15|16|3)',  # execution ids from our results
    ]
    
    for pattern in relevant_patterns:
        matches = re.findall(f".*{pattern}.*", logs, re.IGNORECASE)
        if matches:
            print(f"\n📌 Pattern: {pattern}")
            for match in matches[-5:]:  # Last 5 matches
                print(f"   {match[:120]}")

print("\n" + "="*80)
print("🔍 CHECKING METRICS.PY SOURCE:")

try:
    from src.evaluation.metrics import evaluer_context_precision, evaluer_context_recall, _appeler_juge_une_fois
    import inspect
    
    # Check context_precision
    print("\n1. evaluer_context_precision():")
    source = inspect.getsource(evaluer_context_precision)
    lines = source.split('\n')[:15]
    for line in lines:
        print(f"   {line}")
    
    print("\n2. evaluer_context_recall():")
    source = inspect.getsource(evaluer_context_recall)
    lines = source.split('\n')[:15]
    for line in lines:
        print(f"   {line}")
    
    print("\n3. _appeler_juge_une_fois() - JSON parsing:")
    source = inspect.getsource(_appeler_juge_une_fois)
    # Find JSON parsing section
    start_idx = source.find("json.loads")
    if start_idx != -1:
        relevant_section = source[max(0, start_idx-200):start_idx+300]
        for line in relevant_section.split('\n'):
            print(f"   {line}")
    
except Exception as e:
    print(f"❌ Error: {e}")
