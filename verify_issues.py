#!/usr/bin/env python3
"""
Verify the two issues reported:
1. Department count (4 vs 6)
2. Justification metric labels
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.database.connection import engine
from src.dashboard.justifications import generate_consolidateur_justification

print('='*80)
print('ISSUE VERIFICATION')
print('='*80)
print()

# ============================================================================
# ISSUE 1: Department count
# ============================================================================

print('ISSUE 1: Department Count (4 vs 6)')
print('='*80)
print()

with engine.connect() as conn:
    # Get all departments
    dept_query = text("""
        SELECT DISTINCT departement
        FROM scenarios
        ORDER BY departement
    """)
    
    departments = [row[0] for row in conn.execute(dept_query).fetchall()]
    
    print(f'Total unique departments: {len(departments)}')
    print()
    print('All departments:')
    for i, dept in enumerate(departments, 1):
        # Count scenarios per department
        scenario_count = conn.execute(
            text("SELECT COUNT(*) FROM scenarios WHERE departement = :dept"),
            {"dept": dept}
        ).scalar()
        
        # Count executions per department
        exec_count = conn.execute(
            text("""
                SELECT COUNT(DISTINCT e.id) FROM executions e
                JOIN scenarios s ON s.id = e.scenario_id
                WHERE s.departement = :dept
            """),
            {"dept": dept}
        ).scalar()
        
        print(f'  {i}. {dept}')
        print(f'     - Scenarios: {scenario_count}')
        print(f'     - Executions: {exec_count}')
    
    print()
    print(f'Expected (from Phase 0): 6 departments')
    print(f'Actual: {len(departments)} departments')
    
    if len(departments) == 6:
        print('✓ MATCHES: 6 departments confirmed')
    elif len(departments) == 4:
        print('❌ MISMATCH: Only 4 departments found (missing 2)')
    else:
        print(f'⚠️ UNEXPECTED: {len(departments)} departments (expected 6)')

print()
print()

# ============================================================================
# ISSUE 2: Justification metric label bug
# ============================================================================

print('ISSUE 2: Justification Metric Label Bug')
print('='*80)
print()

# Find a department with data
with engine.connect() as conn:
    test_dept_query = text("""
        SELECT s.departement
        FROM scenarios s
        JOIN executions e ON e.scenario_id = s.id
        GROUP BY s.departement
        LIMIT 1
    """)
    
    test_dept = conn.execute(test_dept_query).scalar()

if not test_dept:
    print('❌ No departments with data found')
    sys.exit(1)

print(f'Testing with department: {test_dept}')
print()

# Get best model
with engine.connect() as conn:
    model_query = text("""
        SELECT m.nom
        FROM modeles m
        JOIN executions e ON e.modele_id = m.id
        JOIN scenarios s ON s.id = e.scenario_id
        WHERE s.departement = :dept
        GROUP BY m.nom
        HAVING COUNT(e.id) >= 2
        LIMIT 1
    """)
    
    model = conn.execute(model_query, {"dept": test_dept}).scalar()

if not model:
    print('⚠ No model with >= 2 executions found')
    sys.exit(1)

print(f'Testing with model: {model}')
print()

# Generate justification
justification = generate_consolidateur_justification(test_dept, model)

print('Returned metrics:')
print('-'*80)
for metric_name, metric_value in justification['metrics'].items():
    if metric_value is not None:
        if isinstance(metric_value, float) and metric_name.startswith('avg_'):
            if metric_value <= 1.0 and metric_name not in ['avg_latency']:
                print(f'  {metric_name}: {metric_value:.1%}')
            else:
                print(f'  {metric_name}: {metric_value:.2f}')
        else:
            print(f'  {metric_name}: {metric_value}')

print()
print('Weaknesses identified (from code):')
print('-'*80)
for weakness in justification['weaknesses']:
    print(f'  • {weakness}')

print()
print('Justification text excerpt:')
print('-'*80)
# Extract areas for improvement section
lines = justification['justification_text'].split('\n')
in_improvements = False
for line in lines:
    if 'Areas for Improvement' in line:
        in_improvements = True
    if in_improvements:
        print(line)
        if line.strip().startswith('###') and 'Areas' not in line:
            break

print()

# Now check the actual metric mapping in the code
print('='*80)
print('Code Analysis: src/dashboard/justifications.py')
print('='*80)
print()

with open('src/dashboard/justifications.py', 'r') as f:
    content = f.read()
    
# Extract the metric aggregation part
import re

# Find where metrics are computed
metric_map = re.findall(r"'(\w+)'.*?(\w+)\)", content)
print('Metric names found in code:')
for pattern in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
    if pattern in content:
        print(f'  ✓ {pattern}')
    else:
        print(f'  ❌ {pattern}')

print()

# Check the weaknesses computation
if 'sorted_metrics[-1]' in content or 'sorted_metrics[-2]' in content:
    print('Weaknesses are assigned from:')
    print('  sorted_metrics[-1] = lowest metric value')
    print('  sorted_metrics[-2] = second-lowest metric value')
    print()
    print('Label reference in code:')
    # Find the exact label assignment
    weakness_section = re.search(
        r'weaknesses = \[(.*?)\]',
        content,
        re.DOTALL
    )
    if weakness_section:
        print(weakness_section.group(0)[:200])

print()
print('='*80)
print('CONCLUSION')
print('='*80)
print()

# Check if context_precision is actually in weaknesses
if justification['weaknesses']:
    for weakness in justification['weaknesses']:
        if 'context precision' in weakness.lower():
            print('✓ Context Precision IS a real metric (found in weaknesses)')
            break
    else:
        print('❌ Context Precision NOT found in weaknesses - metric label mismatch?')
else:
    print('⚠ No weaknesses found (insufficient metrics)')

print()
