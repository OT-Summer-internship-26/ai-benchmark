"""Test if dashboard query works with current database"""
from sqlalchemy import create_engine, text
import pandas as pd
from src.config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL)

print("=" * 80)
print("TESTING DASHBOARD SCORES QUERY")
print("=" * 80)

# Test 1: Check what criteria exist
print("\n1. Unique criteria in scores table:")
with engine.connect() as conn:
    result = conn.execute(text("SELECT DISTINCT critere FROM scores ORDER BY critere"))
    criteria = [r[0] for r in result.fetchall()]
    for c in criteria:
        print(f"   - {c}")

# Test 2: Count scores by criteria
print("\n2. Score counts by criteria:")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT critere, COUNT(*) as count
        FROM scores
        GROUP BY critere
        ORDER BY count DESC
    """))
    for row in result.fetchall():
        print(f"   - {row[0]:30s}: {row[1]:3d} scores")

# Test 3: Try the dashboard query
print("\n3. Testing dashboard query (last 20 scores):")
with engine.connect() as conn:
    scores = pd.read_sql(text("""
        SELECT execution_id, critere, note
        FROM scores
        WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
        ORDER BY execution_id DESC
        LIMIT 20
    """), conn)
    
    print(f"\n   Found {len(scores)} score rows")
    if not scores.empty:
        print("\n   Sample data:")
        print(scores.head(10))
        
        # Pivot to see how it looks
        print("\n4. Pivoted view (as dashboard sees it):")
        pivot = scores.pivot_table(
            index="execution_id",
            columns="critere",
            values="note",
            aggfunc="first"
        )
        print(pivot.head())
    else:
        print("   ⚠️  No Ragas scores found!")
