#!/usr/bin/env python3
"""
scripts/diagnose_ragas_gaps.py
==============================
READ-ONLY diagnostic.  Does NOT write to the database or modify any source file.

For every execution in the database, classifies each of the three
context-dependent RAGAS metrics (faithfulness, context_precision,
context_recall) into exactly one bucket:

  A  no_rag_context   -- search_similar returns [] or only high-distance chunks
  B  no_ground_truth  -- chunks_rag non-empty, but sortie_attendue is NULL/empty
                         (context_recall structurally non-computable -- by design)
  C  judge_call_failed -- chunks + sortie_attendue both present, but the score
                          row is missing or note=NULL in the scores table
  D  score_present    -- a real, non-NULL note exists in the scores table

Reports:
  - Per-department / per-metric bucket counts and percentages
  - For bucket A: actual distances returned by pgvector for up to 10 samples
  - For bucket C: any matching ERROR / WARNING lines in logs/benchmark.log

answer_relevancy is NOT classified here (it never needs RAG context or
sortie_attendue, so it follows a simpler two-bucket C/D split reported
separately).

Usage:
    python -m scripts.diagnose_ragas_gaps
    # or
    python scripts/diagnose_ragas_gaps.py
"""

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup -- make sure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from src.database.connection import engine
from src.rag.embeddings import get_embedding

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Metrics that require RAG context (chunks_rag must be non-empty)
CONTEXT_METRICS = ["faithfulness", "context_precision", "context_recall"]
# Metric that only needs the question+answer
RELEVANCY_METRIC = "answer_relevancy"

# Distance threshold above which chunks are considered "near-irrelevant".
# pgvector <-> operator returns L2 distance for vector(384).
# Values near 0 = identical; values >> 1.0 typically indicate no semantic overlap.
DISTANCE_THRESHOLD_IRRELEVANT = 1.20  # flag if ALL top-k chunks exceed this

TOP_K = 8

LOG_FILE = PROJECT_ROOT / "logs" / "benchmark.log"

SEPARATOR = "=" * 78


# ---------------------------------------------------------------------------
# Helper: fetch all executions with their scenario metadata
# ---------------------------------------------------------------------------
def fetch_all_executions(conn):
    rows = conn.execute(text("""
        SELECT
            e.id            AS execution_id,
            e.scenario_id,
            e.date_execution,
            s.departement,
            s.nom_cas_usage AS scenario_name,
            s.prompt,
            s.sortie_attendue,
            m.nom           AS modele_nom
        FROM executions e
        JOIN scenarios   s ON s.id = e.scenario_id
        JOIN modeles     m ON m.id = e.modele_id
        ORDER BY s.departement, e.id
    """)).mappings().fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Helper: fetch existing scores for all executions (batched)
# ---------------------------------------------------------------------------
def fetch_all_scores(conn):
    """
    Returns dict: {execution_id: {critere: note_or_None}}
    Includes rows where note IS NULL (inserted but judge returned None).
    """
    rows = conn.execute(text("""
        SELECT execution_id, critere, note
        FROM scores
        WHERE critere IN (
            'faithfulness', 'context_precision', 'context_recall', 'answer_relevancy'
        )
    """)).fetchall()

    result = defaultdict(dict)
    for execution_id, critere, note in rows:
        result[execution_id][critere] = note  # note can be float or None
    return dict(result)


# ---------------------------------------------------------------------------
# Helper: compute distances for a single scenario prompt + department
# ---------------------------------------------------------------------------
def get_distances(query, departement, top_k=TOP_K):
    """
    Runs pgvector similarity search and returns list of (contenu, distance).
    Returns [] if the table has no rows for this department.
    Never raises -- returns [] on any exception.
    """
    try:
        emb = get_embedding(query)
        emb_str = "[" + ",".join(str(x) for x in emb) + "]"
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    contenu,
                    embedding <-> CAST(:emb AS vector) AS distance
                FROM documents_vectorises
                WHERE departement = :dep
                ORDER BY distance ASC
                LIMIT :k
            """), {"emb": emb_str, "dep": departement, "k": top_k}).fetchall()
        return [(r[0], float(r[1])) for r in rows]
    except Exception as exc:
        return []


# ---------------------------------------------------------------------------
# Helper: count indexed chunks per department (cheap)
# ---------------------------------------------------------------------------
def get_chunk_counts(conn):
    """Returns {departement: chunk_count}."""
    rows = conn.execute(text("""
        SELECT departement, COUNT(*) AS cnt
        FROM documents_vectorises
        GROUP BY departement
    """)).fetchall()
    return {r[0]: r[1] for r in rows}


# ---------------------------------------------------------------------------
# Helper: scan benchmark.log for lines mentioning a set of execution_ids
# ---------------------------------------------------------------------------
def grep_log_for_executions(execution_ids, max_lines_per_id=5):
    """
    Scans logs/benchmark.log for lines that:
    - Contain any of the given execution_id numbers
    - AND contain error/warning/exception/judge related keywords

    Returns dict: {execution_id: [list of matching log lines]}
    """
    if not execution_ids:
        return {}

    if not LOG_FILE.exists():
        return {eid: ["[LOG FILE NOT FOUND]"] for eid in execution_ids}

    id_set = set(str(eid) for eid in execution_ids)
    error_pattern = re.compile(
        r"(ERROR|error|WARNING|warning|Exception|Traceback|failed|"
        r"None|rate.limit|RateLimit|timeout|Timeout|juge|judge|"
        r"Echec|echec|JUGE|GEMINI|Gemini)",
        re.IGNORECASE,
    )

    hits = defaultdict(list)
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line_stripped = line.rstrip()
                for eid in id_set:
                    if re.search(
                        r"(?:execution_id=|execution |exec_id=|exec |id=)" + eid + r"\b",
                        line_stripped
                    ):
                        if error_pattern.search(line_stripped):
                            if len(hits[int(eid)]) < max_lines_per_id:
                                hits[int(eid)].append(line_stripped)
                        break
    except Exception as exc:
        return {eid: ["[ERROR READING LOG: {}]".format(exc)] for eid in execution_ids}

    return dict(hits)


# ---------------------------------------------------------------------------
# Core classification logic
# ---------------------------------------------------------------------------
def classify_executions(executions, all_scores, chunk_counts):
    """
    Returns:
    {
      departement: {
        metric: {
          "A": [...],   # no_rag_context
          "B": [...],   # no_ground_truth
          "C": [...],   # judge_call_failed
          "D": [...],   # score_present
        }
      }
    }
    """
    all_indexed_depts = set(chunk_counts.keys())
    zero_chunk_depts = {d for d, c in chunk_counts.items() if c == 0}

    result = defaultdict(lambda: defaultdict(lambda: {"A": [], "B": [], "C": [], "D": []}))

    for exec_ in executions:
        eid = exec_["execution_id"]
        dept = exec_["departement"]
        scores_for_exec = all_scores.get(eid, {})
        sortie_non_empty = bool(
            exec_.get("sortie_attendue") and
            str(exec_["sortie_attendue"]).strip()
        )
        dept_has_no_chunks = (dept not in all_indexed_depts) or (dept in zero_chunk_depts)

        for metric in CONTEXT_METRICS:
            entry = {
                "execution_id": eid,
                "scenario_id": exec_["scenario_id"],
                "scenario_name": exec_["scenario_name"],
                "modele_nom": exec_["modele_nom"],
                "departement": dept,
                "prompt": exec_["prompt"],
                "sortie_attendue": exec_.get("sortie_attendue"),
                "date_execution": exec_.get("date_execution"),
            }

            # --- Bucket D: score row exists with a non-NULL note ---
            if metric in scores_for_exec and scores_for_exec[metric] is not None:
                result[dept][metric]["D"].append(entry)
                continue

            # --- Bucket A: no RAG context at dept level ---
            if dept_has_no_chunks:
                entry["dept_chunk_count"] = chunk_counts.get(dept, 0)
                result[dept][metric]["A"].append(entry)
                continue

            # context_recall also requires sortie_attendue
            if metric == "context_recall" and not sortie_non_empty:
                result[dept][metric]["B"].append(entry)
                continue

            # --- Bucket C: context present (and sortie if needed) but score missing/NULL ---
            result[dept][metric]["C"].append(entry)

        # --- answer_relevancy: two-bucket (C vs D) ---
        ar_score = scores_for_exec.get(RELEVANCY_METRIC)
        ar_entry = {
            "execution_id": eid,
            "scenario_id": exec_["scenario_id"],
            "scenario_name": exec_["scenario_name"],
            "modele_nom": exec_["modele_nom"],
            "departement": dept,
            "date_execution": exec_.get("date_execution"),
        }
        if ar_score is not None:
            result[dept][RELEVANCY_METRIC]["D"].append(ar_entry)
        else:
            result[dept][RELEVANCY_METRIC]["C"].append(ar_entry)

    return result


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def pct(n, total):
    if total == 0:
        return "  N/A"
    return "{:5.1f}%".format(100 * n / total)


def print_bucket_table(classification, metrics=None):
    if metrics is None:
        metrics = CONTEXT_METRICS + [RELEVANCY_METRIC]

    all_depts = sorted(classification.keys())

    print("\n{:<36} {:<20} {:>5} {:>5} {:>5} {:>5} {:>6}  {}    {}    {}    {}".format(
        "Dept", "Metric", "A", "B", "C", "D", "Total", "A%  ", "B%  ", "C%  ", "D%  "
    ))
    print("-" * 110)

    totals = defaultdict(lambda: {"A": 0, "B": 0, "C": 0, "D": 0})

    for dept in all_depts:
        for metric in metrics:
            buckets = classification[dept][metric]
            a = len(buckets["A"])
            b = len(buckets["B"])
            c = len(buckets["C"])
            d = len(buckets["D"])
            total = a + b + c + d
            for k in "ABCD":
                totals[metric][k] += len(buckets[k])
            print("{:<36} {:<20} {:>5} {:>5} {:>5} {:>5} {:>6}  {}  {}  {}  {}".format(
                dept[:35], metric, a, b, c, d, total,
                pct(a, total), pct(b, total), pct(c, total), pct(d, total)
            ))

    print("=" * 110)
    for metric in metrics:
        a = totals[metric]["A"]
        b = totals[metric]["B"]
        c = totals[metric]["C"]
        d = totals[metric]["D"]
        total = a + b + c + d
        print("{:<36} {:<20} {:>5} {:>5} {:>5} {:>5} {:>6}  {}  {}  {}  {}".format(
            "TOTAL", metric, a, b, c, d, total,
            pct(a, total), pct(b, total), pct(c, total), pct(d, total)
        ))


def print_bucket_a_samples(classification, sample_limit=10):
    """For each dept with bucket-A entries, print actual pgvector distances."""
    print("\n\n" + SEPARATOR)
    print("BUCKET A -- no_rag_context: CHUNK DISTANCE SAMPLES (up to 10 per dept)")
    print(SEPARATOR)

    dept_prompt_cache = {}
    seen_exec_ids = set()

    for dept in sorted(classification.keys()):
        bucket_a_execs = []
        for metric in CONTEXT_METRICS:
            for entry in classification[dept][metric]["A"]:
                if entry["execution_id"] not in seen_exec_ids:
                    bucket_a_execs.append(entry)
                    seen_exec_ids.add(entry["execution_id"])

        if not bucket_a_execs:
            continue

        sample = bucket_a_execs[:sample_limit]
        print("\n>  Dept: {}  ({} execution(s) in bucket A)".format(dept, len(bucket_a_execs)))
        print("   Dept chunk count in DB: {}".format(sample[0].get("dept_chunk_count", "unknown")))
        print("   Showing {} sample(s):\n".format(len(sample)))

        for entry in sample:
            prompt_key = (dept, entry["prompt"][:120])
            if prompt_key not in dept_prompt_cache:
                print("   -> exec_id={} | {} | {}".format(
                    entry["execution_id"], entry["modele_nom"], entry["scenario_name"][:50]
                ))
                sys.stdout.write("      Fetching distances from pgvector... ")
                sys.stdout.flush()
                distances = get_distances(entry["prompt"], dept, top_k=TOP_K)
                dept_prompt_cache[prompt_key] = distances
                if not distances:
                    print("NO ROWS RETURNED (table empty for this dept)")
                else:
                    print("{} chunks retrieved".format(len(distances)))
                    for i, (chunk_text, dist) in enumerate(distances, 1):
                        if dist < 1.0:
                            relevance = "OK"
                        elif dist < DISTANCE_THRESHOLD_IRRELEVANT:
                            relevance = "~~"
                        else:
                            relevance = "!!"
                        print("      [{}] chunk {}: distance={:.4f} | {}...".format(
                            relevance, i, dist,
                            chunk_text[:80].replace("\n", " ")
                        ))
            else:
                distances = dept_prompt_cache[prompt_key]
                print("   -> exec_id={} | {} | {}".format(
                    entry["execution_id"], entry["modele_nom"], entry["scenario_name"][:50]
                ))
                if distances:
                    dist_summary = ", ".join("{:.4f}".format(d) for _, d in distances[:3])
                    print("      (same dept, distances: [{}, ...])".format(dist_summary))
                else:
                    print("      NO CHUNKS in table for this dept")


def print_bucket_c_details(classification, all_executions_by_id):
    print("\n\n" + SEPARATOR)
    print("BUCKET C -- judge_call_failed: SUSPICIOUS MISSING SCORES")
    print(SEPARATOR)

    c_exec_ids_per_metric = defaultdict(list)
    c_entries_all = {}

    for dept in sorted(classification.keys()):
        for metric in CONTEXT_METRICS + [RELEVANCY_METRIC]:
            for entry in classification[dept][metric]["C"]:
                eid = entry["execution_id"]
                c_exec_ids_per_metric[metric].append(eid)
                c_entries_all[eid] = entry

    all_c_ids = sorted(c_entries_all.keys())

    if not all_c_ids:
        print("\n[OK] No executions in bucket C -- no silent judge failures detected.")
        return

    for metric in CONTEXT_METRICS + [RELEVANCY_METRIC]:
        ids = sorted(set(c_exec_ids_per_metric[metric]))
        if not ids:
            print("\n  {}: (none in bucket C)".format(metric))
            continue
        print("\n  {} -- {} execution(s) in bucket C:".format(metric, len(ids)))
        for eid in ids[:30]:
            e = c_entries_all.get(eid, {})
            print("    exec_id={} | dept={} | model={} | scenario={}".format(
                eid,
                e.get("departement", "?"),
                e.get("modele_nom", "?"),
                e.get("scenario_name", "?")[:45]
            ))
        if len(ids) > 30:
            print("    ... and {} more.".format(len(ids) - 30))

    print("\n--- Grepping {} for error traces on {} execution IDs ---".format(
        LOG_FILE.name, len(all_c_ids)
    ))
    log_hits = grep_log_for_executions(all_c_ids)

    if not log_hits:
        print("  [WARNING] No matching error/warning log lines found for these execution IDs.")
        print("     Possible reasons:")
        print("     - The executions pre-date the current log file (log was rotated)")
        print("     - Exceptions were caught and silently dropped without logging")
        print("     - The execution IDs are not logged with a recognizable pattern")
        print("     => Recommendation: manually check logs/benchmark.log around the")
        print("        date_execution timestamps of the bucket-C entries listed above.")
    else:
        print("  Found log hits for {} execution ID(s):".format(len(log_hits)))
        for eid, lines in sorted(log_hits.items()):
            print("\n  exec_id={}:".format(eid))
            for line in lines:
                print("    {}".format(line[:140]))


def print_relevancy_summary(classification):
    print("\n\n" + SEPARATOR)
    print("answer_relevancy -- SEPARATE TWO-BUCKET SUMMARY (no context/sortie dependency)")
    print(SEPARATOR)
    print("\n{:<36} {:>17} {:>11} {:>7}".format(
        "Dept", "C (missing/NULL)", "D (scored)", "Total"
    ))
    print("-" * 78)
    grand_c = grand_d = 0
    for dept in sorted(classification.keys()):
        c = len(classification[dept][RELEVANCY_METRIC]["C"])
        d = len(classification[dept][RELEVANCY_METRIC]["D"])
        total = c + d
        grand_c += c
        grand_d += d
        print("  {:<35} {:>8} ({})  {:>6} ({})  {:>6}".format(
            dept[:34], c, pct(c, total), d, pct(d, total), total
        ))
    total = grand_c + grand_d
    print("=" * 78)
    print("  {:<35} {:>8} ({})  {:>6} ({})  {:>6}".format(
        "TOTAL", grand_c, pct(grand_c, total), grand_d, pct(grand_d, total), total
    ))


def print_vector_store_summary(chunk_counts, all_depts_in_executions):
    print("\n\n" + SEPARATOR)
    print("VECTOR STORE -- chunk counts per department")
    print(SEPARATOR)
    print("\n  {:<36} {:>15}  {:>15}  {:>10}".format(
        "Dept", "Indexed Chunks", "Has Executions", "Status"
    ))
    print("  " + "-" * 82)

    all_depts = sorted(all_depts_in_executions | set(chunk_counts.keys()))
    for dept in all_depts:
        cnt = chunk_counts.get(dept, 0)
        has_exec = "yes" if dept in all_depts_in_executions else "no"
        if cnt == 0 and dept in all_depts_in_executions:
            status = "[EMPTY]"
        elif cnt == 0:
            status = "no exec"
        else:
            status = "[OK]"
        print("  {:<36} {:>15}  {:>15}  {:>10}".format(
            dept[:35], cnt, has_exec, status
        ))


def print_bucket_c_timestamp_hints(classification):
    """Print date_execution timestamps for bucket C entries to help correlate with logs."""
    print("\n\n" + SEPARATOR)
    print("BUCKET C -- date_execution timestamps (to correlate with log lines)")
    print(SEPARATOR)

    c_entries_per_metric = defaultdict(list)
    for dept in sorted(classification.keys()):
        for metric in CONTEXT_METRICS:
            for entry in classification[dept][metric]["C"]:
                c_entries_per_metric[metric].append(entry)

    for metric in CONTEXT_METRICS:
        entries = sorted(c_entries_per_metric[metric], key=lambda e: e["execution_id"])
        if not entries:
            continue
        unique_execs = {}
        for e in entries:
            if e["execution_id"] not in unique_execs:
                unique_execs[e["execution_id"]] = e
        print("\n  {} ({} unique execution(s)):".format(metric, len(unique_execs)))
        for eid, e in sorted(unique_execs.items())[:20]:
            print("    exec_id={:>6} | {} | date={}".format(
                eid,
                str(e.get("date_execution", "?"))[:19],
                e.get("departement", "?")
            ))
        if len(unique_execs) > 20:
            print("    ... and {} more.".format(len(unique_execs) - 20))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(SEPARATOR)
    print("RAGAS GAPS DIAGNOSTIC  --  READ-ONLY")
    print("Timestamp: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print(SEPARATOR)

    print("\n[1/6] Fetching executions and scenario metadata from DB...")
    with engine.connect() as conn:
        executions = fetch_all_executions(conn)
        all_scores = fetch_all_scores(conn)
        chunk_counts = get_chunk_counts(conn)

    if not executions:
        print("No executions found in the database. Nothing to diagnose.")
        sys.exit(0)

    total_score_rows = sum(len(v) for v in all_scores.values())
    print("     {} execution(s) found.".format(len(executions)))
    print("     {} score row(s) fetched across {} execution(s).".format(
        total_score_rows, len(all_scores)
    ))

    all_depts_in_executions = {e["departement"] for e in executions}

    print("\n[2/6] Classifying executions into buckets A/B/C/D...")
    classification = classify_executions(executions, all_scores, chunk_counts)
    print("     Done.")

    print("\n[3/6] Vector store summary...")
    print_vector_store_summary(chunk_counts, all_depts_in_executions)

    print("\n[4/6] Bucket breakdown table...")
    print("\n" + SEPARATOR)
    print("BUCKET BREAKDOWN -- per department x metric")
    print("Buckets: A=no_rag_context  B=no_ground_truth  C=judge_call_failed  D=score_present")
    print(SEPARATOR)
    print_bucket_table(classification, metrics=CONTEXT_METRICS)

    print_relevancy_summary(classification)

    print("\n[5/6] Bucket A distance samples (calls pgvector -- may take a moment)...")
    print_bucket_a_samples(classification, sample_limit=10)

    print("\n[6/6] Bucket C detail + log grep...")
    all_executions_by_id = {e["execution_id"]: e for e in executions}
    print_bucket_c_details(classification, all_executions_by_id)
    print_bucket_c_timestamp_hints(classification)

    print("\n\n" + SEPARATOR)
    print("DIAGNOSTIC COMPLETE -- no files were modified.")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
