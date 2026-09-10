"""Test dashboard load_executions function directly"""
import sys
sys.path.insert(0, "src")

from sqlalchemy import create_engine, text
from sqlalchemy.sql import bindparam
import pandas as pd
from src.config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL)

print("=" * 80)
print("TESTING DASHBOARD load_executions() LOGIC")
print("=" * 80)

limit = 200

print(f"\n1. Loading executions (limit={limit})...")
limit_clause = "LIMIT :limit" if limit is not None else ""

with engine.connect() as conn:
    executions = pd.read_sql(
        text(
            f"""
            SELECT
                e.id AS execution_id,
                e.scenario_id,
                s.nom_cas_usage,
                s.departement,
                m.id AS modele_id,
                m.nom AS modele_nom,
                e.reponse_generee,
                e.latence_secondes,
                e.cout_estime,
                e.date_execution
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            JOIN modeles m ON m.id = e.modele_id
            ORDER BY e.date_execution DESC
            {limit_clause}
            """
        ),
        conn,
        params={"limit": limit} if limit is not None else {},
    )
    
    print(f"✅ Loaded {len(executions)} executions")
    
    if executions.empty:
        print("⚠️  No executions found!")
        sys.exit(1)
    
    # Load scores
    print("\n2. Loading scores for executions...")
    execution_ids = executions["execution_id"].tolist()
    print(f"   Execution IDs: {len(execution_ids)} total")
    print(f"   First 5 IDs: {execution_ids[:5]}")
    
    scores_query = text(
        "SELECT execution_id, critere, note, commentaire "
        "FROM scores WHERE execution_id IN :ids "
        "AND (critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') "
        "OR (critere='score_global' AND note <= 1.0))"
    ).bindparams(bindparam("ids", expanding=True))
    
    scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})
    
    print(f"✅ Loaded {len(scores)} score rows")
    
    if scores.empty:
        print("⚠️  No scores found for these executions!")
        print("\n   Checking if scores exist at all...")
        result = conn.execute(text("SELECT COUNT(*) FROM scores WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')"))
        total_ragas = result.scalar()
        print(f"   Total Ragas scores in DB: {total_ragas}")
        
        if total_ragas > 0:
            print("\n   Checking which execution_ids have scores...")
            result = conn.execute(text("""
                SELECT DISTINCT execution_id 
                FROM scores 
                WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                ORDER BY execution_id DESC
                LIMIT 10
            """))
            exec_ids_with_scores = [r[0] for r in result.fetchall()]
            print(f"   Exec IDs with scores: {exec_ids_with_scores}")
            print(f"   Overlap with loaded executions: {set(exec_ids_with_scores) & set(execution_ids[:10])}")
        
        sys.exit(1)
    
    print(f"\n3. Pivoting scores...")
    print(f"   Unique criteria: {scores['critere'].unique().tolist()}")
    
    pivot_scores = scores.pivot_table(
        index="execution_id",
        columns="critere",
        values="note",
        aggfunc="first",
    ).reset_index()
    
    print(f"✅ Pivoted {len(pivot_scores)} execution scores")
    print(f"   Columns: {pivot_scores.columns.tolist()}")
    
    print("\n4. Sample pivoted data:")
    print(pivot_scores.head())
    
    print("\n5. Merging with executions...")
    df = executions.merge(pivot_scores, on="execution_id", how="left")
    
    print(f"✅ Final DataFrame: {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()}")
    
    print("\n6. Sample final data (first 5 rows, key columns):")
    display_cols = ['execution_id', 'modele_nom', 'departement', 'faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
    available_cols = [col for col in display_cols if col in df.columns]
    print(df[available_cols].head())
    
    print("\n7. Statistics:")
    if 'faithfulness' in df.columns:
        not_null = df['faithfulness'].notna().sum()
        null = df['faithfulness'].isna().sum()
        print(f"   Faithfulness: {not_null} non-null, {null} null")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE - Dashboard should show scores if this worked!")
    print("=" * 80)
