#!/usr/bin/env python3
"""Test that all Streamlit entry points can be imported correctly."""

import sys
import pathlib

# Set up path like Streamlit does
project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("TESTING STREAMLIT ENTRY POINTS")
print("=" * 80)

# Test 1: admin_dashboard_page.py
print("\n[1/2] Testing admin_dashboard_page.py imports...")
try:
    # Simulate being in the dashboard directory
    _PROJECT_ROOT = pathlib.Path("src/dashboard/admin_dashboard_page.py").resolve().parents[2]
    sys.path.insert(0, str(_PROJECT_ROOT))
    
    from src.dashboard.admin_queries import (
        get_all_departments,
        get_scenarios_for_departments,
        get_models_for_departments,
        get_department_leaderboard,
    )
    from src.dashboard.radar_chart import (
        get_radar_chart_data,
        create_metrics_comparison_table,
    )
    print("  [✓] All imports successful")
    print("  [✓] Entry point: streamlit run src/dashboard/admin_dashboard_page.py")
except Exception as e:
    print(f"  [✗] FAILED: {e}")
    sys.exit(1)

# Test 2: client_recommendation_page.py
print("\n[2/2] Testing client_recommendation_page.py imports...")
try:
    # Simulate being in the dashboard directory
    _PROJECT_ROOT = pathlib.Path("src/dashboard/client_recommendation_page.py").resolve().parents[2]
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    
    from src.dashboard.queries import (
        get_best_model_for_department,
        get_department_summary_stats,
        load_executions_by_department
    )
    from src.dashboard.justifications import generate_consolidateur_justification
    print("  [✓] All imports successful")
    print("  [✓] Entry point: streamlit run src/dashboard/client_recommendation_page.py")
except Exception as e:
    print(f"  [✗] FAILED: {e}")
    sys.exit(1)

# Test 3: app.py (full app with login)
print("\n[3/3] Testing app.py (full app) imports...")
try:
    _PROJECT_ROOT = pathlib.Path("src/dashboard/app.py").resolve().parents[2]
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    
    from src.dashboard.logo import LOGO_B64
    from src.database.connection import engine, SessionLocal
    from src.database.models import Utilisateur, Scenario, Modele
    from src.auth.utils import verify_password, hash_password
    print("  [✓] All imports successful")
    print("  [✓] Entry point: streamlit run src/dashboard/app.py")
except Exception as e:
    print(f"  [✗] FAILED: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL ENTRY POINTS VERIFIED ✓")
print("=" * 80)
print("\nRecommended commands:")
print("  Admin Dashboard:     streamlit run src/dashboard/admin_dashboard_page.py")
print("  Client Page:         streamlit run src/dashboard/client_recommendation_page.py")
print("  Full App (w/ login): streamlit run src/dashboard/app.py")
print("\nOr use the launcher: python run_dashboard.py")
print("=" * 80)
