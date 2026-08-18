#!/usr/bin/env python3
"""
Phase 1 Step 3: Verify existing dashboard queries still work after archiving
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine

def main():
    print('\nPHASE 1 STEP 3 - VERIFY EXISTING DASHBOARD QUERIES')
    print('='*70)

    # Test 1: Original query (should still work)
    print('\n1. Testing ORIGINAL query (from current app.py)...')
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text('''
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
                    LIMIT 10
                '''),
                conn
            )
        print(f'   ✓ Query executed successfully')
        print(f'   ✓ Loaded {len(df)} rows')
        if len(df) > 0:
            print(f'   Sample: {df.iloc[0]["nom_cas_usage"]} / {df.iloc[0]["modele_nom"]}')
    except Exception as e:
        print(f'   ❌ FAILED: {e}')
        return False

    # Test 2: Ragas-only query
    print('\n2. Testing RAGAS-ONLY query (modern approach)...')
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text('''
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
                    LIMIT 10
                '''),
                conn
            )
            
            # Fetch scores (Ragas only)
            if len(df) > 0:
                execution_ids = df['execution_id'].tolist()
                scores = pd.read_sql(
                    text('''
                        SELECT execution_id, critere, note 
                        FROM scores 
                        WHERE execution_id = ANY(:ids)
                        AND is_legacy = FALSE
                        AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                    '''),
                    conn,
                    params={'ids': execution_ids}
                )
            else:
                scores = pd.DataFrame()
        
        print(f'   ✓ Query executed successfully')
        print(f'   ✓ Loaded {len(df)} executions')
        print(f'   ✓ Loaded {len(scores)} Ragas scores (legacy excluded)')
        if len(scores) > 0:
            row = scores.iloc[0]
            print(f'   Sample: {row["critere"]} = {row["note"]}')
    except Exception as e:
        print(f'   ❌ FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Score aggregation logic
    print('\n3. Testing score AGGREGATION (Ragas only)...')
    try:
        with engine.connect() as conn:
            agg_query = text('''
                SELECT
                    e.id,
                    m.nom,
                    AVG(CASE 
                        WHEN s.critere = 'faithfulness' THEN s.note
                        ELSE NULL
                    END) as faithfulness,
                    AVG(CASE 
                        WHEN s.critere = 'answer_relevancy' THEN s.note
                        ELSE NULL
                    END) as answer_relevancy,
                    AVG(CASE 
                        WHEN s.critere = 'context_precision' THEN s.note
                        ELSE NULL
                    END) as context_precision,
                    AVG(CASE 
                        WHEN s.critere = 'context_recall' THEN s.note
                        ELSE NULL
                    END) as context_recall,
                    ((AVG(CASE 
                        WHEN s.critere = 'faithfulness' THEN s.note
                        ELSE NULL
                    END) + AVG(CASE 
                        WHEN s.critere = 'answer_relevancy' THEN s.note
                        ELSE NULL
                    END) + AVG(CASE 
                        WHEN s.critere = 'context_precision' THEN s.note
                        ELSE NULL
                    END) + AVG(CASE 
                        WHEN s.critere = 'context_recall' THEN s.note
                        ELSE NULL
                    END)) / 4.0) as score_global
                FROM executions e
                JOIN modeles m ON m.id = e.modele_id
                LEFT JOIN scores s ON s.execution_id = e.id AND s.is_legacy = FALSE
                GROUP BY e.id, m.nom
                LIMIT 5
            ''')
            agg_df = pd.read_sql(agg_query, conn)
        
        print(f'   ✓ Aggregation query executed successfully')
        print(f'   ✓ Loaded {len(agg_df)} aggregated rows')
        if len(agg_df) > 0:
            row = agg_df.iloc[0]
            sg = row['score_global']
            sg_str = f'{sg:.3f}' if pd.notna(sg) else 'N/A'
            print(f'   Sample: {row["nom"]} - score_global={sg_str}')
    except Exception as e:
        print(f'   ❌ FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Verify no data loss
    print('\n4. Verifying data integrity...')
    try:
        with engine.connect() as conn:
            total_scores = conn.execute(text('SELECT COUNT(*) FROM scores')).scalar()
            legacy_scores = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = TRUE')).scalar()
            modern_scores = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE')).scalar()
            
            if total_scores == legacy_scores + modern_scores:
                print(f'   ✓ No data loss: {legacy_scores} + {modern_scores} = {total_scores}')
            else:
                print(f'   ❌ Data loss detected!')
                return False
    except Exception as e:
        print(f'   ❌ FAILED: {e}')
        return False

    print('\n✓ PHASE 1 STEP 3 COMPLETE: All queries work correctly')
    print('='*70)
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
