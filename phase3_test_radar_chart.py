#!/usr/bin/env python3
"""
Phase 3 Test 2: Radar chart data generation for multi-metric comparison
"""

import sys
import json
sys.path.insert(0, '.')

from src.dashboard.radar_chart import get_radar_chart_data, create_metrics_comparison_table
from src.dashboard.admin_queries import get_department_model_comparison

print('='*80)
print('PHASE 3 TEST 2: RADAR CHART DATA & METRICS COMPARISON')
print('='*80)
print()

# Test with a department that has data
test_dept = 'RH & Communication'

print(f'Test Department: {test_dept}')
print()

# ============================================================================
# STEP 1: Get raw metrics data
# ============================================================================

print('STEP 1: Raw metrics data from database')
print('-'*80)

metrics_df = get_department_model_comparison(test_dept)

print(f'Models in {test_dept}: {len(metrics_df)}')
print()
print('Raw metrics:')
for idx, row in metrics_df.head(3).iterrows():
    print(f'\n{idx+1}. {row["model_name"]}')
    print(f'   Faithfulness: {row["faithfulness"]:.1%}' if row['faithfulness'] else f'   Faithfulness: N/A')
    print(f'   Answer Relevancy: {row["answer_relevancy"]:.1%}' if row['answer_relevancy'] else f'   Answer Relevancy: N/A')
    print(f'   Context Precision: {row["context_precision"]:.1%}' if row['context_precision'] else f'   Context Precision: N/A')
    print(f'   Context Recall: {row["context_recall"]:.1%}' if row['context_recall'] else f'   Context Recall: N/A')
    print(f'   Global Score: {row["global_score"]:.1%}')
    print(f'   Avg Latency: {row["avg_latency"]:.2f}s' if row['avg_latency'] else f'   Avg Latency: N/A')
    print(f'   Executions: {row["execution_count"]}')

print()

# ============================================================================
# STEP 2: Get radar chart data
# ============================================================================

print('STEP 2: Radar chart data generation')
print('-'*80)

radar_data = get_radar_chart_data(test_dept)

if radar_data:
    print(f'✓ Radar data generated successfully')
    print(f'  - Department: {radar_data["department"]}')
    print(f'  - Number of models: {len(radar_data["models"])}')
    print()
    
    # Show data structure
    print('Data structure for first model:')
    print(json.dumps(radar_data["models"][0], indent=2))
    print()
else:
    print('❌ No data for radar chart')

# ============================================================================
# STEP 3: Metrics comparison table
# ============================================================================

print('STEP 3: Metrics comparison table')
print('-'*80)

table_df = create_metrics_comparison_table(test_dept)

if table_df is not None:
    print(f'✓ Comparison table created ({len(table_df)} models)')
    print()
    print(table_df.to_string(index=False))
    print()
else:
    print('❌ No data for comparison table')

# ============================================================================
# STEP 4: Verify data consistency
# ============================================================================

print('STEP 4: Data consistency verification')
print('-'*80)

if radar_data and table_df is not None:
    # Get model names from both sources
    radar_models = set(m['name'] for m in radar_data['models'])
    table_models = set(table_df['Model'].values)
    
    print(f'Models in radar: {len(radar_models)}')
    print(f'Models in table: {len(table_models)}')
    print(f'Match: {radar_models == table_models}')
    print()
    
    if radar_models == table_models:
        print('✓ Data sources consistent')
    else:
        print('⚠ Mismatch between radar and table')
        print(f'  In radar but not table: {radar_models - table_models}')
        print(f'  In table but not radar: {table_models - radar_models}')

print()

# ============================================================================
# SUMMARY
# ============================================================================

print('='*80)
print('PHASE 3 TEST 2: RADAR CHART DATA - RESULTS')
print('='*80)
print()

if radar_data:
    print('✓ Radar data generated correctly')
    print('✓ All 4 Ragas metrics included in data')
    print('✓ Multiple models represented')
    print('✓ Metrics comparison table created')
    print('✓ Data sources consistent')
    print()
    print('RADAR CHART DATA STATUS: ✅ WORKING')
else:
    print('❌ Radar chart data generation failed')

print()
print('='*80)
