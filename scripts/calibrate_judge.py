"""
calibrate_judge.py — Dry-run calibration of the LLM judge (no DB writes).

For each sampled execution, we:
  1. Retrieve the existing RAGAS scores from DB (old scores)
  2. Retrieve RAG chunks for the scenario
  3. Call the judge on all 4 metrics (faithfulness, answer_relevancy,
     context_precision, context_recall)
  4. Compare old vs new and print a summary table

Usage:
  python scripts/calibrate_judge.py [--sample N]  (default N=10)

Output:
  - OLD vs NEW table per execution
  - Count of None per metric
  - Share of exact 0.0 among valid scores
  - Number of Groq API calls made
  - Extrapolated cost for 390 executions vs daily quota

IMPORTANT: This script never writes to the database.
"""

import sys
import os
import time
import pathlib
import argparse

# Ensure UTF-8 output (Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text, create_engine
from src.config.settings import DATABASE_URL
from src.evaluation.metrics import (
    MODELE_JUGE,
    REPETITIONS_JUGE,
    evaluer_faithfulness,
    evaluer_answer_relevancy,
    evaluer_context_precision,
    evaluer_context_recall,
)
from src.rag.vector_store import search_similar

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def fetch_sample(engine, n: int) -> list[dict]:
    """
    Fetch a representative sample of N executions that have at least 1
    non-legacy ragas score. We pick 2-3 per department for diversity.
    """
    query = text("""
        SELECT
            e.id AS execution_id,
            e.reponse_generee,
            s.prompt,
            s.sortie_attendue,
            s.departement,
            m.nom AS model_name
        FROM executions e
        JOIN scenarios s ON e.scenario_id = s.id
        JOIN modeles m ON e.modele_id = m.id
        WHERE e.reponse_generee IS NOT NULL
          AND e.reponse_generee != ''
          AND EXISTS (
              SELECT 1 FROM scores sc
              WHERE sc.execution_id = e.id
                AND sc.methode = 'ragas'
                AND COALESCE(sc.is_legacy, FALSE) = FALSE
          )
        ORDER BY s.departement, e.id
        LIMIT :n
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"n": n}).mappings().fetchall()
    return [dict(r) for r in rows]


def fetch_old_scores(engine, execution_id: int) -> dict:
    """Fetch existing non-legacy RAGAS scores for an execution."""
    query = text("""
        SELECT critere, note
        FROM scores
        WHERE execution_id = :eid
          AND methode = 'ragas'
          AND COALESCE(is_legacy, FALSE) = FALSE
          AND critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"eid": execution_id}).fetchall()
    return {critere: note for critere, note in rows}


def run_calibration(sample_size: int = 10):
    engine = create_engine(DATABASE_URL)

    print("=" * 80)
    print("CALIBRATE JUDGE — DRY RUN (no DB writes)")
    print("=" * 80)
    print(f"  Judge model  : {MODELE_JUGE}")
    print(f"  Repetitions  : {REPETITIONS_JUGE}")
    print(f"  Sample size  : {sample_size}")
    print()

    print(f"Fetching {sample_size} representative executions from DB...")
    sample = fetch_sample(engine, sample_size)
    if not sample:
        print("[ERROR] No eligible executions found. Ensure the DB has non-legacy RAGAS scores.")
        return

    print(f"  -> {len(sample)} executions loaded.\n")

    # Tracking
    groq_calls = 0
    results = []
    none_counts = {m: 0 for m in METRICS}
    zero_counts = {m: 0 for m in METRICS}
    valid_counts = {m: 0 for m in METRICS}

    for idx, row in enumerate(sample, 1):
        exec_id = row["execution_id"]
        dept = row["departement"]
        question = row["prompt"]
        reponse = row["reponse_generee"]
        sortie_attendue = row.get("sortie_attendue") or ""
        model_name = row["model_name"]

        print(f"[{idx:>2}/{len(sample)}] Exec {exec_id:>4} | {model_name} | {dept}")

        # Fetch old scores
        old_scores = fetch_old_scores(engine, exec_id)

        # Retrieve RAG chunks
        try:
            chunks = search_similar(query=question, departement=dept, top_k=4)
        except Exception as e:
            chunks = []
            print(f"   WARNING: RAG retrieval failed: {e}")

        # Run judge on all 4 metrics (DRY RUN — not saved)
        new_scores = {}
        t0 = time.time()

        # faithfulness
        try:
            res = evaluer_faithfulness(reponse, chunks)
            new_scores["faithfulness"] = res.get("note")
            groq_calls += REPETITIONS_JUGE
            time.sleep(0.8)
        except Exception as e:
            new_scores["faithfulness"] = None
            print(f"   ERROR faithfulness: {e}")

        # answer_relevancy
        try:
            res = evaluer_answer_relevancy(reponse, question)
            new_scores["answer_relevancy"] = res.get("note")
            groq_calls += REPETITIONS_JUGE
            time.sleep(0.8)
        except Exception as e:
            new_scores["answer_relevancy"] = None
            print(f"   ERROR answer_relevancy: {e}")

        # context_precision
        try:
            res = evaluer_context_precision(chunks, question)
            new_scores["context_precision"] = res.get("note")
            groq_calls += REPETITIONS_JUGE
            time.sleep(0.8)
        except Exception as e:
            new_scores["context_precision"] = None
            print(f"   ERROR context_precision: {e}")

        # context_recall
        try:
            res = evaluer_context_recall(chunks, sortie_attendue)
            new_scores["context_recall"] = res.get("note")
            groq_calls += REPETITIONS_JUGE
            time.sleep(0.8)
        except Exception as e:
            new_scores["context_recall"] = None
            print(f"   ERROR context_recall: {e}")

        elapsed = time.time() - t0

        # Track stats
        for m in METRICS:
            nv = new_scores.get(m)
            if nv is None:
                none_counts[m] += 1
            else:
                valid_counts[m] += 1
                if nv == 0.0:
                    zero_counts[m] += 1

        results.append({
            "exec_id": exec_id,
            "dept": dept,
            "model": model_name,
            "old": old_scores,
            "new": new_scores,
            "elapsed": elapsed,
        })

        # Print per-execution delta
        for m in METRICS:
            old_v = old_scores.get(m)
            new_v = new_scores.get(m)
            old_str = f"{old_v:.3f}" if old_v is not None else "N/A"
            new_str = f"{new_v:.3f}" if new_v is not None else "None"
            delta_str = ""
            if old_v is not None and new_v is not None:
                delta = new_v - old_v
                delta_str = f" (Δ {delta:+.3f})"
            print(f"   {m:<22}: old={old_str}  new={new_str}{delta_str}")
        print(f"   elapsed: {elapsed:.1f}s")
        print()

    # ----------------------------------------------------------------
    # SUMMARY TABLE
    # ----------------------------------------------------------------
    print()
    print("=" * 80)
    print("OLD vs NEW SUMMARY TABLE")
    print("=" * 80)
    print(f"  {'ExecID':>6} | {'Dept':<28} | {'Metric':<22} | {'OLD':>6} | {'NEW':>6} | {'Delta':>7}")
    print(f"  {'-'*6}-+-{'-'*28}-+-{'-'*22}-+-{'-'*6}-+-{'-'*6}-+-{'-'*7}")

    for r in results:
        for m in METRICS:
            old_v = r["old"].get(m)
            new_v = r["new"].get(m)
            old_str = f"{old_v:.3f}" if old_v is not None else "  N/A "
            new_str = f"{new_v:.3f}" if new_v is not None else "  None"
            if old_v is not None and new_v is not None:
                delta_str = f"{(new_v - old_v):+.3f}"
            elif new_v is None:
                delta_str = " NONE "
            else:
                delta_str = "  N/A "
            print(f"  {r['exec_id']:>6} | {r['dept']:<28} | {m:<22} | {old_str:>6} | {new_str:>6} | {delta_str:>7}")

    # ----------------------------------------------------------------
    # STATISTICS
    # ----------------------------------------------------------------
    print()
    print("=" * 80)
    print("STATISTICS (over the sample)")
    print("=" * 80)

    total_new_scores = sum(valid_counts.values()) + sum(none_counts.values())
    total_none = sum(none_counts.values())
    total_zeros = sum(zero_counts.values())
    total_valid = sum(valid_counts.values())
    zero_pct = (total_zeros / total_valid * 100) if total_valid > 0 else 0.0

    print(f"\n  None per metric:")
    for m in METRICS:
        n = none_counts[m]
        v = valid_counts[m]
        total = n + v
        pct = n / total * 100 if total > 0 else 0
        print(f"    {m:<22}: {n}/{total} = {pct:.1f}% None")

    print(f"\n  Exact 0.0 among valid new scores:")
    for m in METRICS:
        z = zero_counts[m]
        v = valid_counts[m]
        pct = z / v * 100 if v > 0 else 0
        print(f"    {m:<22}: {z}/{v} = {pct:.1f}% exact 0.0")

    print(f"\n  Total None (all metrics combined): {total_none} / {total_new_scores} = {total_none/total_new_scores*100:.1f}%")
    print(f"  Total exact 0.0 (valid only)     : {total_zeros} / {total_valid} = {zero_pct:.1f}%")

    # ----------------------------------------------------------------
    # GROQ CALL COUNT & QUOTA EXTRAPOLATION
    # ----------------------------------------------------------------
    print()
    print("=" * 80)
    print("GROQ CALLS & QUOTA EXTRAPOLATION")
    print("=" * 80)

    n_exec = len(sample)
    metrics_per_exec = 4 * REPETITIONS_JUGE   # 4 metrics × repetitions each
    calls_per_exec = metrics_per_exec

    print(f"\n  Actual Groq calls in this dry-run : {groq_calls}")
    print(f"  Executions processed              : {n_exec}")
    calls_per_exec_actual = groq_calls / n_exec if n_exec else 0
    print(f"  Avg Groq calls per execution      : {calls_per_exec_actual:.1f}")

    # Estimate tokens per call: faithfulness ~ 2000 tokens, others ~600
    # Using max_tokens from the metrics.py:
    #   faithfulness: max_tokens=1800, others: max_tokens=800
    # Rough estimate: average ~1000 output tokens per call
    # Groq daily limit for openai/gpt-oss-20b: ~6000 RPD (requests per day)
    # or token-based limit. Assume 6000 RPD as conservative.
    GROQ_DAILY_RPD = 6000  # conservative for reasoning models on free tier
    # Tokens per day limit (free tier openai/gpt-oss-20b): ~60k tokens/day typical
    # Let's use both metrics

    # Token estimate per execution (very rough):
    # faithfulness: ~300 input tokens (prompt) + ~300 output = 600 tokens
    # answer_relevancy, context_precision, context_recall: ~200 input + 200 output = 400 tokens each
    # Total estimate per execution: 600 + 400*3 = 1800 tokens (conservative)
    EST_TOKENS_PER_EXEC = 1800  # very rough estimate

    total_execs = 390
    extrapolated_calls = int(calls_per_exec_actual * total_execs)
    extrapolated_tokens = EST_TOKENS_PER_EXEC * total_execs

    print(f"\n  --- Extrapolation for {total_execs} executions ---")
    print(f"  Extrapolated Groq calls           : {extrapolated_calls}")
    print(f"  Estimated tokens (rough)          : {extrapolated_tokens:,}")
    print(f"  Daily quota (RPD estimate)        : {GROQ_DAILY_RPD}")

    if extrapolated_calls > 0:
        days_needed_rpd = extrapolated_calls / GROQ_DAILY_RPD
        print(f"  Days needed (RPD basis)           : {days_needed_rpd:.1f} day(s)")
        execs_per_day = int(GROQ_DAILY_RPD / calls_per_exec_actual) if calls_per_exec_actual > 0 else 0
        print(f"  Executions processable per day    : ~{execs_per_day}")
        remaining_days = max(0, (total_execs - n_exec) / execs_per_day) if execs_per_day > 0 else float("inf")
        print(f"  Remaining days after this session : ~{remaining_days:.1f}")

    print()
    print("=" * 80)
    print("DRY RUN COMPLETE — Nothing was written to the database.")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate the LLM judge on a sample of executions (dry run).")
    parser.add_argument("--sample", type=int, default=10, help="Number of executions to sample (default: 10)")
    args = parser.parse_args()

    try:
        run_calibration(sample_size=args.sample)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Dry-run aborted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
