#!/usr/bin/env python3
"""
Phase 1 verification script - test all data layer functions
"""
import sys
sys.path.insert(0, '.')

from src.dashboard.filters import (
    get_all_departments,
    get_scenarios_by_department,
    get_scenarios_for_departments,
    get_models_for_scenarios,
    get_all_models,
)
from src.dashboard.queries import (
    load_executions_by_department,
    load_executions_for_departments,
    get_best_model_for_department,
    get_department_summary_stats,
)


def test_filters():
    print("\n" + "="*70)
    print("PHASE 1 - DATA LAYER VERIFICATION")
    print("="*70)
    
    # Test 1: Get all departments
    print("\n1. GET ALL DEPARTMENTS")
    print("-" * 70)
    depts = get_all_departments()
    print(f"✓ Found {len(depts)} departments:")
    for i, dept in enumerate(depts, 1):
        print(f"  {i}. {dept}")
    
    if not depts:
        print("⚠ ERROR: No departments found!")
        return False
    
    # Test 2: Get scenarios for first department
    print(f"\n2. GET SCENARIOS FOR '{depts[0]}'")
    print("-" * 70)
    scenarios = get_scenarios_by_department(depts[0])
    print(f"✓ Found {len(scenarios)} scenarios:")
    for i, sc in enumerate(scenarios, 1):
        print(f"  {i}. {sc['nom_cas_usage']} (ID: {sc['id']})")
    
    if not scenarios:
        print("⚠ WARNING: No scenarios for this department")
    
    # Test 3: Get models for scenarios
    print(f"\n3. GET MODELS TESTED ON ABOVE SCENARIOS")
    print("-" * 70)
    scenario_ids = [s['id'] for s in scenarios]
    models = get_models_for_scenarios(scenario_ids)
    print(f"✓ Found {len(models)} models:")
    for i, mod in enumerate(models, 1):
        print(f"  {i}. {mod['nom']}")
    
    # Test 4: Get scenarios for multiple departments
    print(f"\n4. GET SCENARIOS FOR MULTIPLE DEPARTMENTS")
    print("-" * 70)
    multi_depts = depts[:2] if len(depts) > 1 else depts
    print(f"Selecting: {multi_depts}")
    multi_scenarios = get_scenarios_for_departments(multi_depts)
    print(f"✓ Found {len(multi_scenarios)} scenarios across {len(multi_depts)} departments")
    
    # Test 5: Get all models
    print(f"\n5. GET ALL MODELS IN SYSTEM")
    print("-" * 70)
    all_models = get_all_models()
    print(f"✓ Found {len(all_models)} models total:")
    for i, mod in enumerate(all_models, 1):
        print(f"  {i}. {mod['nom']}")
    
    return True


def test_queries():
    print("\n" + "="*70)
    print("PHASE 1 - QUERY LAYER VERIFICATION")
    print("="*70)
    
    # Get a department to test
    depts = get_all_departments()
    if not depts:
        print("⚠ ERROR: No departments to test")
        return False
    
    test_dept = depts[0]
    
    # Test 1: Load executions for single department
    print(f"\n1. LOAD EXECUTIONS FOR DEPARTMENT: '{test_dept}'")
    print("-" * 70)
    df = load_executions_by_department(test_dept, limit=50)
    print(f"✓ Loaded {len(df)} executions")
    if len(df) > 0:
        print(f"  Columns: {list(df.columns)}")
        print(f"  Sample execution:")
        row = df.iloc[0]
        print(f"    - Scenario: {row['nom_cas_usage']}")
        print(f"    - Model: {row['modele_nom']}")
        print(f"    - Score: {row['score_global_display']}")
        print(f"    - Latency: {row['latence_secondes']:.2f}s")
    else:
        print("⚠ WARNING: No executions for this department")
    
    # Test 2: Load executions for multiple departments
    print(f"\n2. LOAD EXECUTIONS FOR MULTIPLE DEPARTMENTS")
    print("-" * 70)
    multi_depts = depts[:2] if len(depts) > 1 else depts
    print(f"Selecting: {multi_depts}")
    df_multi = load_executions_for_departments(multi_depts, limit=50)
    print(f"✓ Loaded {len(df_multi)} executions")
    if len(df_multi) > 0:
        unique_depts = df_multi['departement'].unique()
        print(f"  Departments in result: {list(unique_depts)}")
    
    # Test 3: Get best model for department
    print(f"\n3. GET BEST MODEL FOR DEPARTMENT: '{test_dept}'")
    print("-" * 70)
    best = get_best_model_for_department(test_dept)
    if best:
        print(f"✓ Found best model:")
        print(f"  Name: {best['model_name']}")
        print(f"  Avg Score: {best['avg_score']}")
        print(f"  Avg Latency: {best['avg_latency']}s")
        print(f"  Scenarios tested: {best['num_scenarios']}")
        print(f"  Total executions: {best['num_executions']}")
        print(f"  Top scenarios: {best['top_scenarios']}")
    else:
        print("⚠ WARNING: No best model found (insufficient data)")
    
    # Test 4: Get department summary stats
    print(f"\n4. GET DEPARTMENT SUMMARY STATS")
    print("-" * 70)
    stats = get_department_summary_stats(test_dept)
    print(f"✓ Department summary for '{test_dept}':")
    print(f"  Number of scenarios: {stats['num_scenarios']}")
    print(f"  Number of models tested: {stats['num_models_tested']}")
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  First execution: {stats['date_first_execution']}")
    print(f"  Last execution: {stats['date_last_execution']}")
    
    return True


if __name__ == "__main__":
    success = True
    
    try:
        success = test_filters() and success
    except Exception as e:
        print(f"\n❌ FILTER TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    try:
        success = test_queries() and success
    except Exception as e:
        print(f"\n❌ QUERY TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "="*70)
    if success:
        print("✓ PHASE 1 VERIFICATION COMPLETE - ALL TESTS PASSED")
    else:
        print("❌ PHASE 1 VERIFICATION FAILED - SEE ERRORS ABOVE")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)
