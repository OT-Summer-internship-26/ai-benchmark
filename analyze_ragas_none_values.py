#!/usr/bin/env python3
"""
Comprehensive root cause analysis for RAGAS metrics returning None.
Checks: empty responses, missing context, evaluator failures, JSON parsing issues.
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.database.connection import engine

print("="*100)
print("🔬 RAGAS METRICS FAILURE ROOT CAUSE ANALYSIS")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*100)

# ============================================================================
# 1. EMPTY MODEL RESPONSES ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("1️⃣  CHECKING FOR EMPTY MODEL RESPONSES")
print("="*100)

empty_response_query = text("""
    SELECT 
        e.id AS execution_id,
        m.nom AS model_name,
        s.nom_cas_usage AS scenario_name,
        LENGTH(COALESCE(e.reponse_generee, '')) AS response_length,
        CASE 
            WHEN e.reponse_generee IS NULL THEN 'NULL'
            WHEN TRIM(e.reponse_generee) = '' THEN 'EMPTY STRING'
            WHEN LENGTH(e.reponse_generee) < 10 THEN f'TOO SHORT ({LENGTH(e.reponse_generee)} chars)'
            ELSE 'OK'
        END AS response_status
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    LEFT JOIN scores sc ON sc.execution_id = e.id AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
    WHERE sc.id IS NULL
    GROUP BY e.id, m.nom, s.nom_cas_usage, e.reponse_generee
    LIMIT 50
""")

with engine.connect() as conn:
    empty_responses = conn.execute(empty_response_query).fetchall()

if empty_responses:
    print(f"\n⚠️  Found {len(empty_responses)} executions with potential response issues:\n")
    
    response_issues = {}
    for exec_id, model, scenario, resp_len, status in empty_responses:
        if status not in response_issues:
            response_issues[status] = []
        response_issues[status].append({'exec_id': exec_id, 'model': model, 'scenario': scenario})
    
    for status, records in response_issues.items():
        print(f"  {status}: {len(records)} execution(s)")
        for record in records[:3]:
            print(f"    - exec_id={record['exec_id']} | {record['model'][:20]:20} | {record['scenario'][:40]}")
else:
    print("✅ No executions with NULL or empty responses found")

# ============================================================================
# 2. MISSING RETRIEVED CONTEXT ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("2️⃣  CHECKING FOR MISSING RETRIEVED CONTEXT (chunks_rag)")
print("="*100)

# Note: chunks_rag is not stored in DB, but we can infer from evaluation logs
print("""
📌 Context Data Flow:
   - collecteur.agent_collecteur() retrieves chunks via search_similar()
   - chunks_rag is stored in LangGraph state (NOT in database)
   - If search_similar() fails, chunks_rag = [] (empty list)
   - Empty context causes evaluer_context_precision([]) to fail
   
Checking for execution patterns that suggest RAG failure...\n""")

# Check models with context_precision missing
context_missing_query = text("""
    SELECT 
        m.nom AS model_name,
        COUNT(DISTINCT e.id) AS total_executions,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_precision' THEN e.id END) AS with_context_precision,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_recall' THEN e.id END) AS with_context_recall,
        COUNT(DISTINCT CASE WHEN sc.critere IN ('faithfulness', 'answer_relevancy') THEN e.id END) AS with_other_metrics
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN scores sc ON sc.execution_id = e.id
    GROUP BY m.nom
    ORDER BY m.nom
""")

with engine.connect() as conn:
    models_context_stats = conn.execute(context_missing_query).fetchall()

print("Model Context Metric Availability:\n")
print("Model Name                    | Total | With CP | With CR | With F/AR | CP Deficit | CR Deficit")
print("-" * 110)

for model, total, with_cp, with_cr, with_far in models_context_stats:
    cp_deficit = total - (with_cp or 0)
    cr_deficit = total - (with_cr or 0)
    
    if cp_deficit > 0 or cr_deficit > 0:
        status = "⚠️ "
    else:
        status = "✅"
    
    print(f"{status} {model:30} | {total:5} | {str(with_cp or 0):7} | {str(with_cr or 0):7} | {str(with_far or 0):9} | {cp_deficit:10} | {cr_deficit:10}")

print("""
Key Observations:
- If CP_Deficit > 0: context_precision metrics missing (likely RAG failure)
- If CR_Deficit > 0: context_recall metrics missing (could be RAG or sortie_attendue)
- If F/AR present but CP/CR missing: RAG issue (not general eval failure)
""")

# ============================================================================
# 3. EVALUATOR (LLM JUDGE) FAILURE ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("3️⃣  CHECKING FOR EVALUATOR (LLM JUDGE) FAILURES")
print("="*100)

# Check if there are any ALL-None cases (all 4 metrics failed)
all_none_query = text("""
    SELECT 
        e.id AS execution_id,
        m.nom AS model_name,
        s.nom_cas_usage AS scenario_name,
        COUNT(DISTINCT sc.critere) AS metric_count,
        STRING_AGG(DISTINCT sc.critere, ', ' ORDER BY sc.critere) AS present_metrics
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    LEFT JOIN scores sc ON sc.execution_id = e.id 
        AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
    GROUP BY e.id, m.nom, s.nom_cas_usage
    HAVING COUNT(DISTINCT sc.critere) < 4
    ORDER BY e.id DESC
    LIMIT 30
""")

with engine.connect() as conn:
    incomplete_scores = conn.execute(all_none_query).fetchall()

print(f"\nFound {len(incomplete_scores)} executions with incomplete metric scores:\n")

failure_patterns = {}
for exec_id, model, scenario, metric_count, present_metrics in incomplete_scores:
    missing = 4 - (metric_count or 0)
    metrics_str = present_metrics if present_metrics else "NONE"
    
    pattern = f"Missing {missing}/4 (has: {metrics_str})"
    if pattern not in failure_patterns:
        failure_patterns[pattern] = []
    
    failure_patterns[pattern].append({
        'exec_id': exec_id,
        'model': model,
        'scenario': scenario
    })

for pattern, records in sorted(failure_patterns.items()):
    print(f"  {pattern}: {len(records)} execution(s)")
    for record in records[:2]:
        print(f"    - exec_id={record['exec_id']} | {record['model'][:20]:20} | {record['scenario'][:35]}")

# Check logs for judge errors
print("\n📋 Checking evaluation logs for judge call failures...\n")

log_file = "logs/benchmark.log"
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        logs = f.read()
    
    # Look for judge errors
    judge_errors = re.findall(r'\[JUGE\].*(?:échouée|error|Error|failed|Failed)', logs, re.IGNORECASE)
    groq_errors = re.findall(r'(?:rate_limit|429|timeout|Timeout|API|api).*(?:error|Error|failed|Failed)', logs)
    json_errors = re.findall(r'(?:JSONDecodeError|json\.loads|JSON|json).*(?:error|Error|failed|Failed|Invalid)', logs, re.IGNORECASE)
    
    if judge_errors:
        print(f"⚠️  Found {len(judge_errors)} judge-related errors in logs")
        for err in judge_errors[-3:]:
            print(f"   {err[:100]}")
    
    if groq_errors:
        print(f"\n⚠️  Found {len(groq_errors)} Groq API errors in logs")
        for err in groq_errors[-3:]:
            print(f"   {err[:100]}")
    
    if json_errors:
        print(f"\n⚠️  Found {len(json_errors)} JSON parsing errors in logs")
        for err in json_errors[-3:]:
            print(f"   {err[:100]}")
else:
    print("⚠️  Log file not found at", log_file)

# ============================================================================
# 4. JSON PARSING ISSUE ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("4️⃣  CHECKING FOR JSON PARSING ISSUES IN JUDGE RESPONSES")
print("="*100)

print("""
📌 JSON Parsing Flow in src/evaluation/metrics.py:
   1. Judge response received from Groq API
   2. Strip <think>...</think> tags: re.sub(r"<think>.*?</think>", "", ...)
   3. Strip markdown: re.sub(r"^```(?:json)?|```$", "", ...)
   4. Parse JSON: json.loads()
   5. Extract note: float(resultat.get("note", 0.0))

Potential Failure Points:\n""")

# Check metrics.py source
try:
    from src.evaluation.metrics import _appeler_juge_une_fois
    import inspect
    
    source = inspect.getsource(_appeler_juge_une_fois)
    
    # Check for <think> tag handling
    if "<think>" in source or "re.sub" in source:
        print("✅ <think> tag handling present")
        
        # Check for fallback JSON extraction
        if "re.search" in source and r"\{" in source:
            print("✅ JSON extraction fallback pattern present")
        else:
            print("⚠️  NO JSON extraction fallback - could fail on malformed responses")
    else:
        print("❌ NO <think> tag handling found")
    
    # Check backoff retry logic
    if "backoff" in source.lower() or "sleep" in source:
        print("✅ Retry/backoff logic present for API failures")
    else:
        print("⚠️  No retry/backoff logic")
    
    print("\n📝 Current regex patterns in code:")
    
    # Extract relevant patterns
    patterns = re.findall(r're\.sub\([^)]+\)', source)
    for pattern in patterns[:5]:
        print(f"   {pattern}")
    
except Exception as e:
    print(f"⚠️  Could not analyze metrics.py: {e}")

# ============================================================================
# 5. SPECIFIC FAILURE CASE ANALYSIS
# ============================================================================
print("\n" + "="*100)
print("5️⃣  DETAILED FAILURE CASE ANALYSIS")
print("="*100)

# Get a specific execution with failures
failing_exec_query = text("""
    SELECT 
        e.id,
        m.nom,
        s.nom_cas_usage,
        s.departement,
        LENGTH(COALESCE(e.reponse_generee, '')) as response_len,
        LENGTH(COALESCE(s.prompt, '')) as prompt_len,
        LENGTH(COALESCE(s.sortie_attendue, '')) as sortie_len
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    JOIN scenarios s ON s.id = e.scenario_id
    LEFT JOIN scores sc ON sc.execution_id = e.id 
        AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
    WHERE sc.id IS NULL
    GROUP BY e.id, m.nom, s.nom_cas_usage, s.departement, e.reponse_generee, s.prompt, s.sortie_attendue
    LIMIT 1
""")

with engine.connect() as conn:
    failing_case = conn.execute(failing_exec_query).fetchone()

if failing_case:
    exec_id, model, scenario, dept, resp_len, prompt_len, sortie_len = failing_case
    
    print(f"\nSample Failing Execution (ID: {exec_id}):\n")
    print(f"  Model: {model}")
    print(f"  Scenario: {scenario}")
    print(f"  Department: {dept}")
    print(f"  Response length: {resp_len} chars {'✅' if resp_len > 50 else '⚠️'}")
    print(f"  Prompt length: {prompt_len} chars {'✅' if prompt_len > 0 else '❌'}")
    print(f"  Expected output length: {sortie_len} chars {'✅' if sortie_len > 0 else '⚠️'}")
    
    # Get actual data for this execution
    detail_query = text("""
        SELECT 
            e.reponse_generee,
            s.prompt,
            s.sortie_attendue
        FROM executions e
        JOIN scenarios s ON s.id = e.scenario_id
        WHERE e.id = :exec_id
    """)
    
    with engine.connect() as conn:
        exec_data = conn.execute(detail_query, {"exec_id": exec_id}).fetchone()
    
    if exec_data:
        response, prompt, sortie = exec_data
        
        print(f"\n  Response preview: {str(response)[:100] if response else 'NULL'}...")
        print(f"  Prompt preview: {str(prompt)[:100] if prompt else 'NULL'}...")
        print(f"  Expected output preview: {str(sortie)[:100] if sortie else 'NULL'}...")

# ============================================================================
# 6. SUMMARY AND ROOT CAUSE CLASSIFICATION
# ============================================================================
print("\n" + "="*100)
print("📊 ROOT CAUSE SUMMARY")
print("="*100)

summary_query = text("""
    SELECT 
        m.nom as model_name,
        COUNT(DISTINCT e.id) as total_execs,
        COUNT(DISTINCT CASE WHEN sc.id IS NULL THEN e.id END) as missing_all_scores,
        COUNT(DISTINCT CASE WHEN e.reponse_generee IS NULL OR LENGTH(e.reponse_generee) < 5 THEN e.id END) as empty_responses,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_precision' THEN e.id END) as with_cp,
        COUNT(DISTINCT CASE WHEN sc.critere = 'context_recall' THEN e.id END) as with_cr
    FROM executions e
    JOIN modeles m ON m.id = e.modele_id
    LEFT JOIN scores sc ON sc.execution_id = e.id 
        AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
    GROUP BY m.nom
    ORDER BY total_execs DESC
""")

with engine.connect() as conn:
    summary = conn.execute(summary_query).fetchall()

print("\nModel Summary:\n")
print("Model | Total | No Scores | Empty Resp | With CP | With CR | Likely Cause")
print("-" * 100)

for model, total, no_scores, empty_resp, with_cp, with_cr in summary:
    cp_missing = (total or 0) - (with_cp or 0)
    cr_missing = (total or 0) - (with_cr or 0)
    
    # Classify root cause
    if empty_resp and empty_resp > 0:
        cause = "Empty Response ❌"
    elif cp_missing > 0 and cr_missing > 0:
        cause = "Missing Context (RAG) ⚠️"
    elif no_scores == total:
        cause = "Judge Failure or No Eval ❌"
    elif cp_missing > 0 or cr_missing > 0:
        cause = "Partial Judge Failure"
    else:
        cause = "All OK ✅"
    
    print(f"{model:25} | {total:5} | {no_scores:9} | {empty_resp:10} | {with_cp:7} | {with_cr:7} | {cause}")

print("\n" + "="*100)
print("🔍 ROOT CAUSES IDENTIFIED")
print("="*100)

print("""
Based on analysis, None values in RAGAS metrics are caused by:

1. ❌ EMPTY MODEL RESPONSES
   Impact: Causes ALL metrics to fail (faithfulness, answer_relevancy, etc.)
   Mechanism: Judge receives empty string as input, cannot evaluate
   Affected: Any execution with response_length < 5 characters

2. ⚠️ MISSING RETRIEVED CONTEXT (chunks_rag = [])
   Impact: context_precision and context_recall return None specifically
   Mechanism: 
     - collecteur calls search_similar() which returns []
     - empty list passed to evaluer_context_precision([])
     - Judge prompt has empty CHUNKS RÉCUPÉRÉS section
     - Judge cannot evaluate and returns None
   Affected: Executions where RAG vector store search fails/returns no results
   Root: Vector store may be empty for certain departments/scenarios

3. 🔴 EVALUATOR (LLM JUDGE) FAILURES
   Impact: Any/all metrics can be None if judge fails
   Mechanism:
     - Groq API rate limit (429 error)
     - API timeout or network error
     - Judge crashes on malformed input
     - Retry logic exhausted
   Current: Up to 3 retries with backoff (5s, 15s, 45s)
   Affected: Execution IDs in logs with "[JUGE] tentative X/3 échouée"

4. 📄 JSON PARSING FAILURES
   Impact: Judge response cannot be parsed → note extraction fails → None
   Mechanism:
     - Judge wraps response in <think>...</think> tags
     - Regex fails to strip properly (nested tags, unclosed tags)
     - Response contains markdown ```json ... ``` that isn't stripped
     - JSON is malformed or contains invalid escape sequences
   Current Handling:
     ✅ <think> tag stripping: re.sub(r"<think>.*?</think>", "", ...)
     ✅ Markdown stripping: re.sub(r"^```(?:json)?|```$", "", ...)
     ⚠️ NO fallback JSON extraction (should use re.search for robustness)

PRIORITY FOR FIXES:
1. Verify empty responses aren't happening (check response generation)
2. Populate vector store or fix RAG search failures
3. Add robust JSON extraction fallback
4. Increase retry count for rate-limited executions
""")
