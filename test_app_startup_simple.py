#!/usr/bin/env python3
"""
Simple app startup test: verify all imports work
"""

import sys
sys.path.insert(0, '.')

print('='*80)
print('APP STARTUP TEST')
print('='*80)
print()

errors = []

# Test core dependencies
print('Step 1: Core dependencies')
print('-'*80)

deps = {
    'streamlit': 'import streamlit as st',
    'pandas': 'import pandas as pd',
    'plotly': 'import plotly.graph_objects as go',
    'sqlalchemy': 'from sqlalchemy import text',
    'requests': 'import requests',
    'pydantic': 'import pydantic',
    'transformers': 'import transformers',
}

for pkg, import_stmt in deps.items():
    try:
        exec(import_stmt)
        print(f'  [OK] {pkg}')
    except Exception as e:
        print(f'  [FAIL] {pkg}: {e}')
        errors.append(f'{pkg}: {e}')

print()

# Test database connection
print('Step 2: Database connection')
print('-'*80)

try:
    from src.database.connection import engine
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('  [OK] Database connected')
except Exception as e:
    print(f'  [FAIL] Database: {e}')
    errors.append(f'Database: {e}')

print()

# Test admin queries
print('Step 3: Admin query functions')
print('-'*80)

try:
    from src.dashboard.admin_queries import (
        get_all_departments,
        get_department_leaderboard,
    )
    depts = get_all_departments()
    print(f'  [OK] admin_queries (loaded {len(depts)} departments)')
except Exception as e:
    print(f'  [FAIL] admin_queries: {e}')
    errors.append(f'admin_queries: {e}')

print()

# Test radar chart
print('Step 4: Radar chart functions')
print('-'*80)

try:
    from src.dashboard.radar_chart import get_radar_chart_data
    print('  [OK] radar_chart imported')
except Exception as e:
    print(f'  [FAIL] radar_chart: {e}')
    errors.append(f'radar_chart: {e}')

print()

# Test dashboard pages
print('Step 5: Dashboard page imports')
print('-'*80)

try:
    # Don't run the page, just check it imports
    import importlib.util
    spec = importlib.util.spec_from_file_location("admin_dashboard_page", 
                                                   "src/dashboard/admin_dashboard_page.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print('  [OK] admin_dashboard_page.py loads')
except Exception as e:
    print(f'  [FAIL] admin_dashboard_page.py: {e}')
    errors.append(f'admin_dashboard_page: {e}')

print()

# Summary
print('='*80)
print('RESULTS')
print('='*80)
print()

if not errors:
    print('[SUCCESS] All imports successful')
    print()
    print('App is ready to start:')
    print('  streamlit run src/dashboard/admin_dashboard_page.py')
    print()
else:
    print(f'[FAILED] {len(errors)} error(s):')
    for err in errors:
        print(f'  - {err}')
    sys.exit(1)

print('='*80)
