#!/usr/bin/env python3
"""
Final verification that both Streamlit entry points are production-ready.
Tests import paths work correctly when running from project root.
"""

import sys
import pathlib
import subprocess
import time

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("\n" + "=" * 80)
print("FINAL VERIFICATION: STREAMLIT ENTRY POINTS")
print("=" * 80)

# Test 1: Verify path bootstrap in admin_dashboard_page.py
print("\n[TEST 1] Verify admin_dashboard_page.py has path bootstrap...")
with open(PROJECT_ROOT / "src/dashboard/admin_dashboard_page.py", "r", encoding="utf-8") as f:
    content = f.read()
    if "sys.path.insert(0, str(_PROJECT_ROOT))" in content and "import sys" in content:
        print("  [✓] Path bootstrap present")
    else:
        print("  [✗] Path bootstrap MISSING")
        sys.exit(1)

# Test 2: Verify path bootstrap in client_recommendation_page.py
print("\n[TEST 2] Verify client_recommendation_page.py has path bootstrap...")
with open(PROJECT_ROOT / "src/dashboard/client_recommendation_page.py", "r", encoding="utf-8") as f:
    content = f.read()
    if "sys.path.insert(0, str(_PROJECT_ROOT))" in content and "import sys" in content:
        print("  [✓] Path bootstrap present")
    else:
        print("  [✗] Path bootstrap MISSING")
        sys.exit(1)

# Test 3: Import test for admin_dashboard_page.py
print("\n[TEST 3] Test admin_dashboard_page.py imports (simulating streamlit run)...")
try:
    # This simulates what Streamlit does when you run:
    #   streamlit run src/dashboard/admin_dashboard_page.py
    
    # Create a namespace as if we're in the script
    script_path = PROJECT_ROOT / "src/dashboard/admin_dashboard_page.py"
    script_dir = script_path.parent
    
    # Add script dir to path (what Streamlit does)
    test_path = str(script_dir)
    if test_path in sys.path:
        sys.path.remove(test_path)
    sys.path.insert(0, test_path)
    
    # Now simulate the path bootstrap
    _PROJECT_ROOT = script_path.resolve().parents[2]
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    
    # Try imports
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
    import streamlit  # Verify Streamlit is available
    
    print("  [✓] All imports successful")
    print("  [✓] Ready for: streamlit run src/dashboard/admin_dashboard_page.py")
    
except Exception as e:
    print(f"  [✗] FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Import test for client_recommendation_page.py
print("\n[TEST 4] Test client_recommendation_page.py imports (simulating streamlit run)...")
try:
    # Reset sys.path
    if test_path in sys.path:
        sys.path.remove(test_path)
    
    # Simulate Streamlit for client page
    script_path = PROJECT_ROOT / "src/dashboard/client_recommendation_page.py"
    script_dir = script_path.parent
    test_path = str(script_dir)
    
    if test_path in sys.path:
        sys.path.remove(test_path)
    sys.path.insert(0, test_path)
    
    # Path bootstrap
    _PROJECT_ROOT = script_path.resolve().parents[2]
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    
    # Try imports
    from src.dashboard.queries import (
        get_best_model_for_department,
        get_department_summary_stats,
        load_executions_by_department
    )
    from src.dashboard.justifications import generate_consolidateur_justification
    import streamlit  # Verify Streamlit is available
    
    print("  [✓] All imports successful")
    print("  [✓] Ready for: streamlit run src/dashboard/client_recommendation_page.py")
    
except Exception as e:
    print(f"  [✗] FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verify requirements are installed
print("\n[TEST 5] Verify all dependencies are installed...")
required_packages = ["streamlit", "plotly", "requests", "pydantic", "transformers", "pandas", "sqlalchemy"]
missing = []

for package in required_packages:
    try:
        __import__(package)
        print(f"  [✓] {package}")
    except ImportError:
        print(f"  [✗] {package} MISSING")
        missing.append(package)

if missing:
    print(f"\nMissing packages: {', '.join(missing)}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL VERIFICATIONS PASSED ✓")
print("=" * 80)

print("\n📱 LAUNCH COMMANDS:\n")
print("  Admin Dashboard:")
print("    $ streamlit run src/dashboard/admin_dashboard_page.py\n")
print("  Client Page:")
print("    $ streamlit run src/dashboard/client_recommendation_page.py\n")
print("  Full App (Recommended):")
print("    $ streamlit run src/dashboard/app.py\n")
print("  Or use launcher:")
print("    $ python run_dashboard.py\n")

print("=" * 80)
print("App will be available at: http://localhost:8501")
print("=" * 80 + "\n")
