"""
Step 1 diagnostic: run ~10 IT & Architecture scenario prompts through
search_similar() and report the actual L2-distance scores per chunk.

Usage (from project root):
    python -m scripts.diag_it_retrieval        # uses hardcoded IT prompts
"""

import sys
import pathlib

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text
from src.database.connection import engine
from src.rag.embeddings import get_embedding

DEPARTEMENT = "IT & Architecture"
TOP_K = 8  # same as diagnostic_faithfulness.py

# ── fetch IT & Architecture scenario prompts from the DB ─────────────────────
def fetch_it_prompts(limit=12):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, nom_cas_usage, prompt
                FROM scenarios
                WHERE departement = :dept
                ORDER BY id
                LIMIT :limit
            """),
            {"dept": DEPARTEMENT, "limit": limit},
        ).mappings().fetchall()
    return rows


# ── search with distances (modify search_similar inline so we see scores) ────
def search_with_distances(query: str, departement: str, top_k: int = TOP_K):
    query_embedding = get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    contenu,
                    embedding <-> CAST(:embedding AS vector) AS distance,
                    LEFT(contenu, 120) AS preview
                FROM documents_vectorises
                WHERE departement = :departement
                ORDER BY distance ASC
                LIMIT :top_k
            """),
            {"embedding": embedding_str, "departement": departement, "top_k": top_k},
        ).fetchall()
    return result   # list of (contenu, distance, preview)


# ── count total docs indexed for this dept ───────────────────────────────────
def count_indexed(departement: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM documents_vectorises WHERE departement = :dept"),
            {"dept": departement},
        ).fetchone()
    return row[0] if row else 0


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    total_docs = count_indexed(DEPARTEMENT)
    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC RETRIEVAL — département: {DEPARTEMENT}")
    print(f"Total chunks indexed for this dept: {total_docs}")
    print(f"{'='*70}\n")

    prompts = fetch_it_prompts()
    if not prompts:
        print("⚠️  No scenarios found for IT & Architecture in the DB.")
        return

    all_top1_distances = []

    for scen in prompts:
        sid   = scen["id"]
        name  = scen["nom_cas_usage"]
        query = scen["prompt"]

        print(f"\n{'─'*70}")
        print(f"[Scénario {sid}] {name}")
        print(f"Prompt (first 200 chars): {query[:200]}")
        print()

        rows = search_with_distances(query, DEPARTEMENT)

        if not rows:
            print("  ⚠️  No chunks returned (empty corpus for this dept?)")
            continue

        top1_dist = rows[0][1]
        all_top1_distances.append((name, top1_dist))

        for rank, (contenu, dist, preview) in enumerate(rows, 1):
            marker = "★" if rank == 1 else " "
            print(f"  {marker} Rank {rank} | distance={dist:.4f} | preview: {preview!r}")

    # ── summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("SUMMARY — top-1 L2 distances per scenario")
    print(f"{'='*70}")
    for name, dist in sorted(all_top1_distances, key=lambda x: x[1]):
        quality = "✅ close" if dist < 0.8 else ("⚠️  borderline" if dist < 1.2 else "❌ far")
        print(f"  {quality}  dist={dist:.4f}  {name}")

    if all_top1_distances:
        dists = [d for _, d in all_top1_distances]
        print(f"\n  min={min(dists):.4f}  max={max(dists):.4f}  "
              f"mean={sum(dists)/len(dists):.4f}")
    print()


if __name__ == "__main__":
    main()
