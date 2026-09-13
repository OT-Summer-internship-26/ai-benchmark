"""
Multi-department retrieval distance diagnostic.
Usage: python -m scripts.diag_all_depts
"""
import sys, pathlib
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from src.database.connection import engine
from src.rag.embeddings import get_embedding

TOP_K = 8

def count_indexed(dept):
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM documents_vectorises WHERE departement=:d"), {"d": dept}).fetchone()[0]

def fetch_scenarios(dept, limit=16):
    with engine.connect() as conn:
        return conn.execute(text("SELECT id, nom_cas_usage, prompt FROM scenarios WHERE departement=:d ORDER BY id LIMIT :l"), {"d": dept, "l": limit}).mappings().fetchall()

def search_top1(query, dept):
    emb = get_embedding(query)
    es  = "[" + ",".join(str(x) for x in emb) + "]"
    with engine.connect() as conn:
        row = conn.execute(text("SELECT embedding <-> CAST(:e AS vector) AS dist FROM documents_vectorises WHERE departement=:d ORDER BY dist ASC LIMIT 1"), {"e": es, "d": dept}).fetchone()
    return row[0] if row else None

def run_dept(dept):
    total = count_indexed(dept)
    scenarios = fetch_scenarios(dept)
    dists = []
    print(f"\n{'='*74}")
    print(f"DEPT: {dept}  |  chunks: {total}  |  scenarios: {len(scenarios)}")
    print(f"{'='*74}")
    for s in scenarios:
        d = search_top1(s["prompt"], dept)
        if d is None:
            print(f"  XX  [{s['id']:>3}] {s['nom_cas_usage'][:52]:<52} | NO DATA")
            continue
        dists.append(d)
        tag = "OK " if d < 1.0 else ("~~ " if d < 1.5 else ("!! " if d < 2.0 else "XX "))
        print(f"  {tag} [{s['id']:>3}] {s['nom_cas_usage'][:52]:<52} | {d:.4f}")
    if dists:
        print(f"  >> min={min(dists):.4f}  max={max(dists):.4f}  mean={sum(dists)/len(dists):.4f}")
        print(f"  >> below 1.0: {sum(1 for d in dists if d<1.0)}/{len(dists)}  below 1.5: {sum(1 for d in dists if d<1.5)}/{len(dists)}  below 2.0: {sum(1 for d in dists if d<2.0)}/{len(dists)}")
    return dists

def main():
    with engine.connect() as conn:
        depts = [r[0] for r in conn.execute(text("SELECT DISTINCT departement FROM documents_vectorises ORDER BY departement")).fetchall()]
    summary = {}
    for dept in depts:
        summary[dept] = run_dept(dept)
    print(f"\n\n{'='*74}")
    print("GLOBAL SUMMARY")
    print(f"{'='*74}")
    print(f"  {'Dept':<44} | tot_chunks | min    | mean   | max    | <1.0 | <1.5")
    print(f"  {'-'*44}-+-----------+--------+--------+--------+------+------")
    for dept, dists in summary.items():
        n = len(dists)
        if n == 0:
            print(f"  {dept[:44]:<44} | no data"); continue
        mn=min(dists); mx=max(dists); avg=sum(dists)/n
        b10=sum(1 for d in dists if d<1.0); b15=sum(1 for d in dists if d<1.5)
        print(f"  {dept[:44]:<44} | {count_indexed(dept):>9} | {mn:.4f} | {avg:.4f} | {mx:.4f} | {b10:>2}/{n} | {b15:>2}/{n}")

if __name__ == "__main__":
    main()
