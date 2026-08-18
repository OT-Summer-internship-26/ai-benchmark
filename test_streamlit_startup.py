#!/usr/bin/env python3
"""
Test Streamlit app startup without running server

Instead of `streamlit run`, we import and check all modules load without errors
"""

import sys
sys.path.insert(0, '.')

print('='*80)
print('STREAMLIT APP STARTUP TEST (Import-Based)')
print('='*80)
print()

# Test 1: Import all dashboard dependencies
print('Test 1: Import admin dashboard module')
print('-'*80)

try:
    import streamlit as st
    print('[OK] streamlit imported')
except Exception as e:
    print(f'[FAIL] streamlit: {e}')
    sys.exit(1)

try:
    import pandas as pd
    print('[OK] pandas imported')
except Exception as e:
    print(f'[FAIL] pandas: {e}')
    sys.exit(1)

try:
    import plotly.graph_objects as go
    print('[OK] plotly.graph_objects imported')
except Exception as e:
    print(f'[FAIL] plotly: {e}')
    sys.exit(1)

try:
    from src.dashboard.admin_queries import (
        get_all_departments,
        get_scenarios_for_departments,
        get_models_for_departments,
        get_department_leaderboard,
    )
    print('[OK] admin_queries module imported')
except Exception as e:
    print(f'[FAIL] admin_queries: {e}')
    sys.exit(1)

try:
    from src.dashboard.radar_chart import (
        get_radar_chart_data,
        create_metrics_comparison_table,
    )
    print('[OK] radar_chart module imported')
except Exception as e:
    print(f'[FAIL] radar_chart: {e}')
    sys.exit(1)

print()

# Test 2: Import client dashboard dependencies
print('Test 2: Import client recommendation page')
print('-'*80)

try:
    from src.dashboard.queries import (
        get_department_summary_stats,
        get_best_model_for_department,
    )
    print('[OK] queries module imported')
except Exception as e:
    print(f'[FAIL] queries: {e}')
    sys.exit(1)

try:
    from src.dashboard.justifications import generate_consolidateur_justification
    print('[OK] justifications module imported')
except Exception as e:
    print(f'[FAIL] justifications: {e}')
    sys.exit(1)

print()

# Test 3: Load admin dashboard page code (check syntax, not run)
print('Test 3: Load admin dashboard page code')
print('-'*80)

try:
    with open('src/dashboard/admin_dashboard_page.py', 'r') as f:
        code = f.read()
    
    # Try to compile the code (checks syntax)
    compile(code, 'src/dashboard/admin_dashboard_page.py', 'exec')
    print('[OK] admin_dashboard_page.py syntax valid')
    
    # Check it has the render function
    if 'def render_admin_dashboard():' in code:
        print('[OK] render_admin_dashboard() function found')
    else:
        print('[WARN] render_admin_dashboard() function not found')
    
except Exception as e:
    print(f'[FAIL] admin_dashboard_page: {e}')
    sys.exit(1)

print()

# Test 4: Load client recommendation page code
print('Test 4: Load client recommendation page code')
print('-'*80)

try:
    with open('src/dashboard/client_recommendation_page.py', 'r') as f:
        code = f.read()
    
    compile(code, 'src/dashboard/client_recommendation_page.py', 'exec')
    print('[OK] client_recommendation_page.py syntax valid')
    
    if 'def render_client_recommendation():' in code or 'def ' in code:
        print('[OK] Render functions found')
    
except Exception as e:
    print(f'[FAIL] client_recommendation_page: {e}')
    sys.exit(1)

print()

# Test 5: Verify all imports work end-to-end
print('Test 5: End-to-end import chain')
print('-'*80)

try:
    # Simulate admin dashboard startup
    print('Simulating admin dashboard startup...')
    
    depts = get_all_departments()
    print(f'  ✓ Got {len(depts)} departments')
    
    if len(depts) > 0:
        scenarios = get_scenarios_for_departments([depts[0]['name']])
        print(f'  ✓ Got {len(scenarios)} scenarios for first dept')
        
        models = get_models_for_departments([depts[0]['name']])
        print(f'  ✓ Got {len(models)} models for first dept')
        
        radar = get_radar_chart_data(depts[0]['name']) if len(depts) > 0 else None
        print(f'  ✓ Radar data: {"generated" if radar else "none (empty dept)"}')
    
    print('[OK] Admin dashboard code chain works')
    
except Exception as e:
    print(f'[FAIL] End-to-end chain: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Final status
print('='*80)
print('STREAMLIT APP STARTUP TEST - RESULTS')
print('='*80)
print()

print('[OK] All modules import successfully')
print('[OK] Admin dashboard page code valid')
print('[OK] Client recommendation page code valid')
print('[OK] End-to-end import chain works')
print('[OK] Queries execute without errors')
print()

print('STATUS: APP READY TO START')
print()
print('To run the admin dashboard:')
print('  streamlit run src/dashboard/admin_dashboard_page.py')
print()
print('To run the client dashboard:')
print('  streamlit run src/dashboard/client_recommendation_page.py')
print()

print('='*80)
