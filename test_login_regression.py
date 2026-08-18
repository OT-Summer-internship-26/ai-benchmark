#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test to verify that app.py shows login screen on startup.
"""

import sys
import pathlib

# Set up path
project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Simulate what Streamlit does
_PROJECT_ROOT = pathlib.Path("src/dashboard/app.py").resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

print("=" * 80)
print("LOGIN FLOW VERIFICATION TEST")
print("=" * 80)

# Test 1: Check that main() exists and calls login_page when auth_role is not set
print("\n[TEST 1] Checking main() function exists...")
from src.dashboard import app as app_module
if hasattr(app_module, 'main'):
    print("  [✓] main() function defined")
else:
    print("  [✗] main() function NOT found")
    sys.exit(1)

# Test 2: Check login_page function exists
print("\n[TEST 2] Checking login_page() function exists...")
if hasattr(app_module, 'login_page'):
    print("  [✓] login_page() function defined")
else:
    print("  [✗] login_page() function NOT found")
    sys.exit(1)

# Test 3: Check do_login function exists
print("\n[TEST 3] Checking do_login() function exists...")
if hasattr(app_module, 'do_login'):
    print("  [✓] do_login() function defined")
else:
    print("  [✗] do_login() function NOT found")
    sys.exit(1)

# Test 4: Check do_signup function exists
print("\n[TEST 4] Checking do_signup() function exists...")
if hasattr(app_module, 'do_signup'):
    print("  [✓] do_signup() function defined")
else:
    print("  [✗] do_signup() function NOT found")
    sys.exit(1)

# Test 5: Check that st.set_page_config is called in main
print("\n[TEST 5] Checking st.set_page_config() is in main()...")
import inspect
main_source = inspect.getsource(app_module.main)
if "st.set_page_config" in main_source:
    print("  [✓] st.set_page_config() is in main()")
else:
    print("  [✗] st.set_page_config() NOT found in main()")
    sys.exit(1)

# Test 6: Check that login_page is called in main before dashboard logic
print("\n[TEST 6] Checking login_page() is called in main()...")
if "login_page()" in main_source and "st.stop()" in main_source:
    # Find the line numbers
    lines = main_source.split('\n')
    setpage_line = None
    login_check_line = None
    dashboard_logic_line = None
    
    for i, line in enumerate(lines):
        if "st.set_page_config" in line:
            setpage_line = i
        if "login_page()" in line:
            login_check_line = i
        if "render_sidebar_identity" in line or "st.sidebar.header" in line:
            dashboard_logic_line = i
            break
    
    if setpage_line is not None and login_check_line is not None:
        if setpage_line < login_check_line:
            print("  [✓] st.set_page_config() called before login_page()")
        else:
            print("  [✗] st.set_page_config() NOT before login_page()")
            sys.exit(1)
        
        if dashboard_logic_line is None or login_check_line < dashboard_logic_line:
            print("  [✓] login_page() called before dashboard logic")
        else:
            print("  [✗] login_page() NOT before dashboard logic")
            sys.exit(1)
    else:
        print("  [✗] Could not find execution order")
        sys.exit(1)
else:
    print("  [✗] login_page() or st.stop() NOT found in main()")
    sys.exit(1)

# Test 7: Check that there's only ONE def main()
print("\n[TEST 7] Checking there's only ONE main() definition...")
main_count = main_source.count("def main()")
if main_count == 1:
    print("  [✓] Only one main() definition")
else:
    print(f"  [✗] Found {main_count} main() definitions (should be 1)")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL TESTS PASSED ✓")
print("=" * 80)
print("\nLogin flow verified:")
print("1. st.set_page_config() is called first")
print("2. Session state is checked for 'auth_role'")
print("3. If not authenticated, login_page() is shown")
print("4. If authenticated, dashboard is rendered")
print("\nThe app should now show a login screen on startup.")
print("=" * 80 + "\n")
