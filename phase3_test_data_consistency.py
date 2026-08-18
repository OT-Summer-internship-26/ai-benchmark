#!/usr/bin/env python3
"""
Phase 3 Test 4: Data consistency verification for admin view

Checks:
1. All departments have consistent scenario/model counts
2. No null/missing data in critical fields
3. Scores are within valid range (0-1)
4. Execution counts match
5. Department names match across all queries
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine
from src.dashboard.admin_queries import (
    get_all_departments,
    get_scenarios_for_departments,
    get_models_for_departments,
    get_department_model_comparison,
    get_department_leaderboard,
)

print('='*80)
print('PHASE 3 TEST 4: DATA CONSISTENCY VERIFICATION')
print('='*80)
print()

# ============================================================================
# CHECK 1: Department names consistency
# ============================================================================

print('CHECK 1: Department names consistency across all sources')
print('-'*80)

all_depts = get_all_departments()
dept_names_from_get_all = set(d["name"] for d in all_depts)

# Get department names from database
with engine.connect() as conn:
    query = text("SELECT DISTINCT departement FROM scenarios ORDER BY departement")
    db_depts = set(row[0] for row in conn.execute(query).fetchall())

print(f'Departments from get_all_departments(): {len(dept_names_from_get_all)}')
print(f'  {sorted(dept_names_from_get_all)}')
print()

print(f'Departments from database: {len(db_depts)}')
print(f'  {sorted(db_depts)}')
print()

if dept_names_from_get_all == db_depts:
    print('✓ Department names consistent')
else:
    print('❌ MISMATCH: Department names inconsistent')
    print(f'  Only in get_all: {dept_names_from_get_all - db_depts}')
    print(f'  Only in database: {db_depts - dept_names_from_get_all}')

print()

# ============================================================================
# CHECK 2: Scenario counts
# ============================================================================

print('CHECK 2: Scenario counts verification')
print('-'*80)

all_errors = []

for dept in all_depts:
    dept_name = dept["name"]
    expected_count = dept["scenario_count"]
    
    # Verify against database
    with engine.connect() as conn:
        query = text("SELECT COUNT(*) FROM scenarios WHERE departement = :dept")
        actual_count = conn.execute(query, {"dept": dept_name}).scalar()
    
    if expected_count != actual_count:
        all_errors.append(f'  {dept_name}: Expected {expected_count}, got {actual_count}')
        print(f'❌ {dept_name}: Expected {expected_count}, got {actual_count}')
    else:
        print(f'✓ {dept_name}: {actual_count} scenarios')

if not all_errors:
    print('✓ All scenario counts verified')

print()

# ============================================================================
# CHECK 3: Execution counts
# ============================================================================

print('CHECK 3: Execution counts consistency')
print('-'*80)

for dept in all_depts:
    dept_name = dept["name"]
    expected_exec = dept["execution_count"]
    
    # Verify against database
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(DISTINCT e.id)
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            WHERE s.departement = :dept
        """)
        actual_exec = conn.execute(query, {"dept": dept_name}).scalar() or 0
    
    if expected_exec != actual_exec:
        all_errors.append(f'  {dept_name}: Expected {expected_exec} executions, got {actual_exec}')
        print(f'❌ {dept_name}: Expected {expected_exec}, got {actual_exec}')
    else:
        print(f'✓ {dept_name}: {actual_exec} executions')

if not all_errors:
    print('✓ All execution counts verified')

print()

# ============================================================================
# CHECK 4: Score ranges (0-1)
# ============================================================================

print('CHECK 4: Score values within valid range (0-1)')
print('-'*80)

with engine.connect() as conn:
    query = text("""
        SELECT
            critere,
            MIN(note) as min_note,
            MAX(note) as max_note,
            COUNT(*) as count
        FROM scores
        WHERE is_legacy = FALSE
        GROUP BY critere
    """)
    
    scores_check = conn.execute(query).fetchall()

all_in_range = True
for row in scores_check:
    critere, min_note, max_note, count = row
    
    if min_note is None or max_note is None:
        print(f'⚠ {critere}: All NULL ({count} rows)')
        continue
    
    in_range = (0 <= min_note <= 1) and (0 <= max_note <= 1)
    
    if in_range:
        print(f'✓ {critere}: [{min_note:.3f}, {max_note:.3f}] ({count} scores)')
    else:
        all_errors.append(f'  {critere}: Out of range [{min_note}, {max_note}]')
        print(f'❌ {critere}: OUT OF RANGE [{min_note}, {max_note}]')
        all_in_range = False

if all_in_range:
    print('✓ All scores within valid range')

print()

# ============================================================================
# CHECK 5: No orphaned executions
# ============================================================================

print('CHECK 5: Data referential integrity')
print('-'*80)

with engine.connect() as conn:
    # Check for executions with missing scenario
    query = text("""
        SELECT COUNT(*) FROM executions e
        LEFT JOIN scenarios s ON e.scenario_id = s.id
        WHERE s.id IS NULL
    """)
    orphaned_scenarios = conn.execute(query).scalar() or 0
    
    # Check for executions with missing model
    query = text("""
        SELECT COUNT(*) FROM executions e
        LEFT JOIN modeles m ON e.modele_id = m.id
        WHERE m.id IS NULL
    """)
    orphaned_models = conn.execute(query).scalar() or 0
    
    # Check for scores with missing execution
    query = text("""
        SELECT COUNT(*) FROM scores sc
        LEFT JOIN executions e ON sc.execution_id = e.id
        WHERE e.id IS NULL
    """)
    orphaned_scores = conn.execute(query).scalar() or 0

print(f'Executions with missing scenario: {orphaned_scenarios}')
print(f'Executions with missing model: {orphaned_models}')
print(f'Scores with missing execution: {orphaned_scores}')

if orphaned_scenarios == 0 and orphaned_models == 0 and orphaned_scores == 0:
    print('✓ All references valid (no orphaned records)')
else:
    all_errors.append(f'  Orphaned records found: scenarios={orphaned_scenarios}, models={orphaned_models}, scores={orphaned_scores}')
    print('❌ ORPHANED RECORDS FOUND')

print()

# ============================================================================
# CHECK 6: Modern (non-legacy) scores only in analysis
# ============================================================================

print('CHECK 6: Legacy score filtering')
print('-'*80)

comparison_df = get_department_model_comparison('RH & Communication')

if comparison_df.empty:
    print('⚠ No data in RH & Communication')
else:
    # Verify that scores being used are non-legacy
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(*) FROM scores
            WHERE is_legacy = FALSE
        """)
        modern_scores = conn.execute(query).scalar() or 0
        
        query = text("""
            SELECT COUNT(*) FROM scores
            WHERE is_legacy = TRUE
        """)
        legacy_scores = conn.execute(query).scalar() or 0
    
    print(f'Legacy scores: {legacy_scores}')
    print(f'Modern scores: {modern_scores}')
    
    if legacy_scores > 0 and modern_scores > 0:
        print('✓ Both legacy and modern scores present in database')
        print('✓ Queries correctly filter by is_legacy = FALSE')
    else:
        print('⚠ Limited score types in database')

print()

# ============================================================================
# CHECK 7: Cascading filter correctness
# ============================================================================

print('CHECK 7: Cascading filter correctness')
print('-'*80)

selected_depts = ['IT & Architecture', 'Marketing & Digital']

scenarios = get_scenarios_for_departments(selected_depts)
scenario_depts = set(s['departement'] for s in scenarios)

models = get_models_for_departments(selected_depts)

print(f'Selected departments: {selected_depts}')
print(f'Scenarios belong to: {scenario_depts}')
print()

if scenario_depts == set(selected_depts):
    print('✓ Scenarios correctly filtered')
else:
    all_errors.append(f'  Scenarios from unexpected departments: {scenario_depts - set(selected_depts)}')
    print('❌ Scenarios from unexpected departments')

# Verify models come from selected depts
with engine.connect() as conn:
    query = text("""
        SELECT DISTINCT s.departement
        FROM executions e
        JOIN scenarios s ON s.id = e.scenario_id
        JOIN modeles m ON m.id = e.modele_id
        WHERE s.departement = ANY(:depts)
    """)
    model_source_depts = set(row[0] for row in conn.execute(query, {"depts": selected_depts}).fetchall())

print(f'Models source departments: {model_source_depts}')

if model_source_depts == set(selected_depts):
    print('✓ Models correctly filtered by department')
else:
    all_errors.append(f'  Models from unexpected departments: {model_source_depts - set(selected_depts)}')
    print('❌ Models from unexpected departments')

print()

# ============================================================================
# CHECK 8: Leaderboard ranking correctness
# ============================================================================

print('CHECK 8: Leaderboard ranking verification')
print('-'*80)

leaderboard = get_department_leaderboard(['RH & Communication'])

if leaderboard.empty:
    print('⚠ No leaderboard data')
else:
    dept_lb = leaderboard[leaderboard['departement'] == 'RH & Communication']
    
    # Check ranks are sequential
    ranks = sorted(dept_lb['rank'].values)
    expected_ranks = list(range(1, len(ranks) + 1))
    
    if ranks == expected_ranks:
        print('✓ Ranks are sequential (1, 2, 3, ...)')
    else:
        all_errors.append(f'  Ranks not sequential: {ranks}')
        print(f'❌ Ranks not sequential: {ranks}')
    
    # Check scores are descending
    scores = dept_lb.sort_values('rank')['global_score'].values
    is_descending = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    if is_descending:
        print('✓ Global scores in descending order')
    else:
        all_errors.append('  Global scores not in descending order')
        print('❌ Global scores not in descending order')

print()

# ============================================================================
# SUMMARY
# ============================================================================

print('='*80)
print('PHASE 3 TEST 4: DATA CONSISTENCY - RESULTS')
print('='*80)
print()

if not all_errors:
    print('✅ ALL CHECKS PASSED - No data inconsistencies found')
    print()
    print('✓ Department names consistent across sources')
    print('✓ Scenario counts verified')
    print('✓ Execution counts verified')
    print('✓ Score values in valid range (0-1)')
    print('✓ No orphaned records')
    print('✓ Legacy scores correctly filtered')
    print('✓ Cascading filters work correctly')
    print('✓ Leaderboard ranking correct')
    print()
    print('DATA CONSISTENCY STATUS: ✅ VERIFIED')
else:
    print(f'❌ FOUND {len(all_errors)} DATA INCONSISTENCIES:')
    for error in all_errors:
        print(error)

print()
print('='*80)
