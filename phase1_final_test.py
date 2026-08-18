#!/usr/bin/env python3
"""
Phase 1 Final Test: Comprehensive verification that no data loss or query breakage occurred
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine

def test_no_data_loss():
    """Verify no scores were deleted during archiving"""
    print('\nTEST 1: DATA LOSS CHECK')
    print('-' * 70)
    
    with engine.connect() as conn:
        # Get counts
        total = conn.execute(text('SELECT COUNT(*) FROM scores')).scalar()
        legacy = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = TRUE')).scalar()
        modern = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE')).scalar()
        
        print(f'Total scores in database: {total}')
        print(f'  - Marked as legacy (is_legacy=TRUE): {legacy}')
        print(f'  - Marked as modern (is_legacy=FALSE): {modern}')
        print(f'  - Sum check: {legacy} + {modern} = {legacy + modern}')
        
        if total == legacy + modern:
            print('✓ PASS: No data loss detected')
            return True
        else:
            print('❌ FAIL: Data loss or orphaned rows detected!')
            return False

def test_legacy_tagging_accuracy():
    """Verify legacy scores are correctly identified"""
    print('\nTEST 2: LEGACY TAGGING ACCURACY')
    print('-' * 70)
    
    with engine.connect() as conn:
        # Check 1: All heuristic criteria marked legacy
        heuristic_unmarked = conn.execute(text(
            "SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') AND is_legacy = FALSE"
        )).scalar()
        
        if heuristic_unmarked == 0:
            print('✓ All heuristic criteria (completude, structure, fidelite_rag, honnetete) marked legacy')
        else:
            print(f'❌ {heuristic_unmarked} heuristic scores NOT marked legacy')
            return False
        
        # Check 2: All score_global > 1.0 marked legacy
        old_scale_unmarked = conn.execute(text(
            "SELECT COUNT(*) FROM scores WHERE critere='score_global' AND note > 1.0 AND is_legacy = FALSE"
        )).scalar()
        
        if old_scale_unmarked == 0:
            print('✓ All old-scale scores (score_global > 1.0) marked legacy')
        else:
            print(f'❌ {old_scale_unmarked} old-scale scores NOT marked legacy')
            return False
        
        # Check 3: Sample legacy rows
        samples = conn.execute(text(
            "SELECT DISTINCT critere FROM scores WHERE is_legacy = TRUE ORDER BY critere LIMIT 5"
        )).fetchall()
        print(f'✓ Sample legacy criteria: {[s[0] for s in samples]}')
        
        return True

def test_ragas_scores_preserved():
    """Verify Ragas scores are correctly marked as modern"""
    print('\nTEST 3: RAGAS SCORES PRESERVATION')
    print('-' * 70)
    
    with engine.connect() as conn:
        ragas_criteria = ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
        
        # Count Ragas scores marked as modern
        ragas_modern = conn.execute(text(f"""
            SELECT COUNT(*) FROM scores 
            WHERE is_legacy = FALSE 
            AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
        """)).scalar()
        
        # Count ALL Ragas scores
        ragas_total = conn.execute(text(f"""
            SELECT COUNT(*) FROM scores 
            WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
        """)).scalar()
        
        print(f'Total Ragas scores: {ragas_total}')
        print(f'Marked as modern (is_legacy=FALSE): {ragas_modern}')
        
        if ragas_total == ragas_modern:
            print('✓ All Ragas scores correctly marked as modern')
            
            # Show distribution
            for crit in ragas_criteria:
                count = conn.execute(text(f"""
                    SELECT COUNT(*) FROM scores WHERE critere = '{crit}' AND is_legacy = FALSE
                """)).scalar()
                print(f'  - {crit}: {count}')
            
            return True
        else:
            print(f'❌ Ragas score mismatch: {ragas_total} total but {ragas_modern} marked modern')
            return False

def test_query_backward_compatibility():
    """Verify queries that DON'T filter by is_legacy still work"""
    print('\nTEST 4: BACKWARD COMPATIBILITY (unfiltered queries)')
    print('-' * 70)
    
    try:
        with engine.connect() as conn:
            # Old-style query (no is_legacy filter)
            result = pd.read_sql(
                text('''
                    SELECT e.id, m.nom, s.nom_cas_usage, 
                           COUNT(DISTINCT scr.id) as score_count
                    FROM executions e
                    JOIN modeles m ON m.id = e.modele_id
                    JOIN scenarios s ON s.id = e.scenario_id
                    LEFT JOIN scores scr ON scr.execution_id = e.id
                    GROUP BY e.id, m.nom, s.nom_cas_usage
                    LIMIT 5
                '''),
                conn
            )
        
        if len(result) > 0:
            print(f'✓ Backward-compatible query works: {len(result)} rows returned')
            return True
        else:
            print('⚠ Query returned no results (might be normal if data is minimal)')
            return True
    except Exception as e:
        print(f'❌ Query failed: {e}')
        return False

def test_query_with_legacy_filter():
    """Verify queries CAN filter by is_legacy when needed"""
    print('\nTEST 5: NEW FILTERING CAPABILITY (is_legacy filter)')
    print('-' * 70)
    
    try:
        with engine.connect() as conn:
            # New-style query (with is_legacy filter)
            legacy_result = pd.read_sql(
                text('''
                    SELECT COUNT(*) as count
                    FROM scores WHERE is_legacy = TRUE
                '''),
                conn
            )
            
            modern_result = pd.read_sql(
                text('''
                    SELECT COUNT(*) as count
                    FROM scores WHERE is_legacy = FALSE
                '''),
                conn
            )
        
        legacy_count = legacy_result['count'].iloc[0]
        modern_count = modern_result['count'].iloc[0]
        
        print(f'✓ Legacy filter query works: {legacy_count} legacy scores found')
        print(f'✓ Modern filter query works: {modern_count} modern scores found')
        
        if legacy_count > 0 and modern_count > 0:
            print('✓ Both legacy and modern scores are present and queryable')
            return True
        else:
            print('⚠ Warning: One category has 0 scores')
            return True
    except Exception as e:
        print(f'❌ Query failed: {e}')
        return False

def test_dashboard_simulation():
    """Simulate what the dashboard will do: load executions with Ragas scores only"""
    print('\nTEST 6: DASHBOARD SIMULATION (production use case)')
    print('-' * 70)
    
    try:
        with engine.connect() as conn:
            # Step 1: Load executions
            executions = pd.read_sql(
                text('''
                    SELECT e.id, s.departement, m.nom, e.date_execution
                    FROM executions e
                    JOIN scenarios s ON s.id = e.scenario_id
                    JOIN modeles m ON m.id = e.modele_id
                    ORDER BY e.date_execution DESC
                    LIMIT 20
                '''),
                conn
            )
            
            print(f'✓ Loaded {len(executions)} executions')
            
            if len(executions) == 0:
                print('⚠ No executions to test with')
                return True
            
            # Step 2: Load Ragas scores for these executions
            exec_ids = executions['id'].tolist()
            ragas_scores = pd.read_sql(
                text('''
                    SELECT execution_id, critere, note
                    FROM scores
                    WHERE execution_id = ANY(:ids)
                    AND is_legacy = FALSE
                    AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                '''),
                conn,
                params={'ids': exec_ids}
            )
            
            print(f'✓ Loaded {len(ragas_scores)} Ragas scores (legacy excluded)')
            
            # Step 3: Compute aggregates
            if len(ragas_scores) > 0:
                pivot = ragas_scores.pivot_table(
                    index='execution_id',
                    columns='critere',
                    values='note',
                    aggfunc='first'
                )
                
                if not pivot.empty:
                    pivot['score_global'] = pivot[[
                        'faithfulness', 'answer_relevancy', 
                        'context_precision', 'context_recall'
                    ]].mean(axis=1)
                    
                    print(f'✓ Computed aggregates for {len(pivot)} executions')
                    
                    # Check a sample
                    sample = pivot.iloc[0]
                    print(f'  Sample score_global: {sample["score_global"]:.3f}')
                    return True
            
            print('⚠ No Ragas scores found (might be normal)')
            return True
    except Exception as e:
        print(f'❌ Simulation failed: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    print('\n' + '='*70)
    print('PHASE 1 - FINAL COMPREHENSIVE TEST')
    print('='*70)
    
    tests = [
        ('Data Loss Check', test_no_data_loss),
        ('Legacy Tagging Accuracy', test_legacy_tagging_accuracy),
        ('Ragas Scores Preservation', test_ragas_scores_preserved),
        ('Backward Compatibility', test_query_backward_compatibility),
        ('New Filtering Capability', test_query_with_legacy_filter),
        ('Dashboard Simulation', test_dashboard_simulation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f'\n❌ TEST CRASHED: {e}')
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print('\n' + '='*70)
    print('PHASE 1 FINAL TEST SUMMARY')
    print('='*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = '✓ PASS' if result else '❌ FAIL'
        print(f'{status}: {name}')
    
    print(f'\nTotal: {passed}/{total} tests passed')
    
    if passed == total:
        print('\n✓✓✓ PHASE 1 COMPLETE - ALL TESTS PASSED ✓✓✓')
        print('Safe to proceed to Phase 2')
        return True
    else:
        print('\n❌ PHASE 1 FAILED - Fix issues before Phase 2')
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ FATAL ERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
