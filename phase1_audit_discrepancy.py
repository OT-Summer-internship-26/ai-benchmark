#!/usr/bin/env python3
"""
Phase 1 Audit: Investigate the discrepancy in score counts
Run raw SQL queries and show EXACT results
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.database.connection import engine

print('\n' + '='*80)
print('PHASE 1 DISCREPANCY AUDIT - RAW SQL QUERIES')
print('='*80)

with engine.connect() as conn:
    # Query 1: Total scores
    print('\nQUERY 1: Total score count')
    print('-' * 80)
    print('SQL: SELECT COUNT(*) as total FROM scores')
    result = conn.execute(text('SELECT COUNT(*) as total FROM scores')).fetchall()
    print(f'Result: {result}')
    total_count = result[0][0]
    print(f'Total scores in database: {total_count}')
    
    # Query 2: Legacy scores (is_legacy = TRUE)
    print('\nQUERY 2: Legacy scores count (is_legacy = TRUE)')
    print('-' * 80)
    print('SQL: SELECT COUNT(*) as legacy FROM scores WHERE is_legacy = TRUE')
    result = conn.execute(text('SELECT COUNT(*) as legacy FROM scores WHERE is_legacy = TRUE')).fetchall()
    print(f'Result: {result}')
    legacy_count = result[0][0]
    print(f'Legacy scores: {legacy_count}')
    
    # Query 3: Modern scores (is_legacy = FALSE)
    print('\nQUERY 3: Modern scores count (is_legacy = FALSE)')
    print('-' * 80)
    print('SQL: SELECT COUNT(*) as modern FROM scores WHERE is_legacy = FALSE')
    result = conn.execute(text('SELECT COUNT(*) as modern FROM scores WHERE is_legacy = FALSE')).fetchall()
    print(f'Result: {result}')
    modern_count = result[0][0]
    print(f'Modern scores: {modern_count}')
    
    # Query 4: Sum check
    print('\nQUERY 4: Verification sum')
    print('-' * 80)
    print(f'Legacy ({legacy_count}) + Modern ({modern_count}) = {legacy_count + modern_count}')
    print(f'Total in DB: {total_count}')
    if legacy_count + modern_count == total_count:
        print(f'✓ MATCHES: {legacy_count} + {modern_count} = {total_count}')
    else:
        missing = total_count - (legacy_count + modern_count)
        print(f'❌ MISMATCH: Missing {missing} scores')
    
    # Query 5: Modern Ragas by criteria breakdown
    print('\nQUERY 5: Modern Ragas scores by criteria')
    print('-' * 80)
    print('''SQL: SELECT critere, COUNT(*) as count 
    FROM scores 
    WHERE is_legacy = FALSE 
    GROUP BY critere 
    ORDER BY critere''')
    result = conn.execute(text('''
        SELECT critere, COUNT(*) as count 
        FROM scores 
        WHERE is_legacy = FALSE 
        GROUP BY critere 
        ORDER BY critere
    ''')).fetchall()
    print('Result:')
    ragas_total = 0
    for row in result:
        print(f'  {row[0]}: {row[1]}')
        ragas_total += row[1]
    print(f'Sum of all modern criteria: {ragas_total}')
    
    # Query 6: All non-legacy criteria names
    print('\nQUERY 6: All distinct criteria marked as modern (is_legacy = FALSE)')
    print('-' * 80)
    print('''SQL: SELECT DISTINCT critere 
    FROM scores 
    WHERE is_legacy = FALSE 
    ORDER BY critere''')
    result = conn.execute(text('''
        SELECT DISTINCT critere 
        FROM scores 
        WHERE is_legacy = FALSE 
        ORDER BY critere
    ''')).fetchall()
    print('Result:')
    for row in result:
        print(f'  - {row[0]}')
    
    # Query 7: Legacy breakdown
    print('\nQUERY 7: Legacy scores by criteria')
    print('-' * 80)
    print('''SQL: SELECT critere, COUNT(*) as count 
    FROM scores 
    WHERE is_legacy = TRUE 
    GROUP BY critere 
    ORDER BY critere''')
    result = conn.execute(text('''
        SELECT critere, COUNT(*) as count 
        FROM scores 
        WHERE is_legacy = TRUE 
        GROUP BY critere 
        ORDER BY critere
    ''')).fetchall()
    print('Result:')
    legacy_breakdown = 0
    for row in result:
        print(f'  {row[0]}: {row[1]}')
        legacy_breakdown += row[1]
    print(f'Sum of all legacy criteria: {legacy_breakdown}')
    
    # Query 8: Check for NULL is_legacy values
    print('\nQUERY 8: Scores with NULL is_legacy (should be 0)')
    print('-' * 80)
    print('SQL: SELECT COUNT(*) FROM scores WHERE is_legacy IS NULL')
    result = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy IS NULL')).fetchall()
    print(f'Result: {result}')
    null_count = result[0][0]
    print(f'NULL is_legacy values: {null_count}')
    if null_count > 0:
        print(f'❌ WARNING: {null_count} scores have NULL is_legacy!')
    else:
        print('✓ No NULL values')
    
    # Query 9: Ragas-only query (the exact one from test)
    print('\nQUERY 9: Ragas-only query (from Test 3)')
    print('-' * 80)
    print('''SQL: SELECT COUNT(*) FROM scores 
    WHERE is_legacy = FALSE 
    AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')''')
    result = conn.execute(text('''
        SELECT COUNT(*) FROM scores 
        WHERE is_legacy = FALSE 
        AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
    ''')).fetchall()
    print(f'Result: {result}')
    ragas_filtered = result[0][0]
    print(f'Ragas scores (filtered): {ragas_filtered}')
    
    # Query 10: What's in the 99 if not Ragas?
    print('\nQUERY 10: Modern scores NOT in Ragas criteria')
    print('-' * 80)
    print('''SQL: SELECT critere, COUNT(*) as count 
    FROM scores 
    WHERE is_legacy = FALSE 
    AND critere NOT IN ('faithfulness','answer_relevancy','context_precision','context_recall')
    GROUP BY critere
    ORDER BY critere''')
    result = conn.execute(text('''
        SELECT critere, COUNT(*) as count 
        FROM scores 
        WHERE is_legacy = FALSE 
        AND critere NOT IN ('faithfulness','answer_relevancy','context_precision','context_recall')
        GROUP BY critere
        ORDER BY critere
    ''')).fetchall()
    print('Result:')
    other_count = 0
    for row in result:
        print(f'  {row[0]}: {row[1]}')
        other_count += row[1]
    if other_count == 0:
        print('  (none)')
    print(f'Total non-Ragas modern: {other_count}')

print('\n' + '='*80)
print('SUMMARY')
print('='*80)
print(f'Total scores: {total_count}')
print(f'  Legacy (is_legacy=TRUE): {legacy_count}')
print(f'  Modern (is_legacy=FALSE): {modern_count}')
print(f'  NULL is_legacy: {null_count}')
print(f'\nModern breakdown:')
print(f'  - Ragas criteria only: {ragas_filtered}')
print(f'  - Other criteria: {other_count}')
print(f'  - Total modern: {ragas_filtered + other_count}')
print(f'\nVerification:')
print(f'  {legacy_count} + {modern_count} + {null_count} = {legacy_count + modern_count + null_count}')
print(f'  Should equal total: {total_count}')
if legacy_count + modern_count + null_count == total_count:
    print('  ✓ CORRECT')
else:
    print(f'  ❌ MISMATCH: {total_count - (legacy_count + modern_count + null_count)} unaccounted')
print('='*80 + '\n')
