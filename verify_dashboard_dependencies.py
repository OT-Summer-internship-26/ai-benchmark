#!/usr/bin/env python3
"""
Comprehensive dependency verification for the Ooredoo IA Benchmark dashboard.

This script verifies that all required dependencies are installed and can be imported
correctly for the dashboard to function properly.
"""

import sys
import pathlib
import os

# Add project root to path
project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("OOREDOO IA BENCHMARK - DASHBOARD DEPENDENCY VERIFICATION")
print("=" * 80)

# Track results
passed = 0
failed = 0
warnings = 0

def test_import(module_name, description="", required=True):
    """Test importing a module and report results."""
    global passed, failed, warnings
    
    try:
        __import__(module_name)
        print(f"✅ {module_name:<30} {description}")
        passed += 1
        return True
    except ImportError as e:
        if required:
            print(f"❌ {module_name:<30} MISSING: {e}")
            failed += 1
        else:
            print(f"⚠️ {module_name:<30} Optional: {e}")
            warnings += 1
        return False
    except Exception as e:
        print(f"⚠️ {module_name:<30} Warning: {e}")
        warnings += 1
        return False

print("\n🔧 CORE PYTHON LIBRARIES")
print("-" * 40)
test_import("sys", "System functions")
test_import("os", "Operating system interface")
test_import("pathlib", "Path operations")
test_import("typing", "Type hints")
test_import("datetime", "Date/time operations")
test_import("json", "JSON operations")
test_import("io", "I/O operations")

print("\n📊 DATA & WEB LIBRARIES")
print("-" * 40)
test_import("pandas", "Data manipulation")
test_import("numpy", "Numerical operations")
test_import("requests", "HTTP client")
test_import("plotly", "Interactive plotting")
test_import("plotly.graph_objects", "Plotly graph objects")

print("\n🌐 STREAMLIT FRAMEWORK")
print("-" * 40)
test_import("streamlit", "Streamlit web framework")

print("\n🗄️ DATABASE LIBRARIES")
print("-" * 40)
test_import("sqlalchemy", "SQL toolkit")
test_import("sqlalchemy.orm", "ORM functionality")
test_import("psycopg2", "PostgreSQL adapter")
test_import("passlib", "Password hashing")

print("\n🔐 AUTHENTICATION LIBRARIES")
print("-" * 40)
test_import("passlib.context", "Password context")
test_import("passlib.hash", "Password hashing", required=False)

print("\n📁 PROJECT MODULES")
print("-" * 40)

# Core project modules
test_import("src.config.settings", "Application configuration")
test_import("src.database.connection", "Database connection")
test_import("src.database.models", "Database models")
test_import("src.auth.utils", "Authentication utilities")

# Dashboard modules
test_import("src.dashboard.app", "Main dashboard application")
test_import("src.dashboard.admin_dashboard_page", "Admin dashboard page")
test_import("src.dashboard.admin_queries", "Admin database queries")
test_import("src.dashboard.radar_chart", "Radar chart utilities")
test_import("src.dashboard.filters", "Filter utilities")
test_import("src.dashboard.queries", "General database queries")
test_import("src.dashboard.logo", "Logo constants")
test_import("src.dashboard.chart_helpers", "Chart helpers")
test_import("src.dashboard.justifications", "Justification utilities")
test_import("src.dashboard.client_recommendation_page", "Client recommendation page")

print("\n🤖 AI & LLM LIBRARIES")
print("-" * 40)
test_import("langchain", "LangChain framework", required=False)
test_import("openai", "OpenAI API client", required=False)
test_import("anthropic", "Anthropic API client", required=False)
test_import("groq", "Groq API client", required=False)

print("\n🧪 TESTING LIBRARIES")
print("-" * 40)
test_import("pytest", "Testing framework", required=False)

print("\n📋 ENVIRONMENT CONFIGURATION")
print("-" * 40)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv                      Environment file loaded")
    passed += 1
except Exception as e:
    print(f"❌ dotenv                      Failed to load: {e}")
    failed += 1

# Check critical environment variables
critical_vars = ["DATABASE_URL"]
optional_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "OLLAMA_URL"]

for var in critical_vars:
    if os.getenv(var):
        print(f"✅ {var:<30} Configured")
        passed += 1
    else:
        print(f"❌ {var:<30} MISSING")
        failed += 1

for var in optional_vars:
    if os.getenv(var):
        print(f"✅ {var:<30} Configured")
        passed += 1
    else:
        print(f"⚠️ {var:<30} Optional (not set)")
        warnings += 1

print("\n🔍 FUNCTIONAL TESTS")
print("-" * 40)

# Test database connection
try:
    from src.database.connection import check_database_health
    if check_database_health():
        print("✅ Database connection         Working")
        passed += 1
    else:
        print("❌ Database connection         Failed")
        failed += 1
except Exception as e:
    print(f"❌ Database connection         Error: {e}")
    failed += 1

# Test data loading
try:
    from src.dashboard.app import load_executions, load_scenario_catalog
    
    # Test with small limit
    executions = load_executions(limit=1)
    scenarios = load_scenario_catalog()
    
    print(f"✅ Data loading               {len(executions)} executions, {len(scenarios)} scenarios")
    passed += 1
except Exception as e:
    print(f"❌ Data loading               Error: {e}")
    failed += 1

# Test authentication
try:
    from src.auth.utils import login
    # Don't actually test login to avoid database hits
    print("✅ Authentication utilities   Available")
    passed += 1
except Exception as e:
    print(f"❌ Authentication utilities   Error: {e}")
    failed += 1

print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

print(f"✅ Passed:   {passed}")
if warnings > 0:
    print(f"⚠️ Warnings: {warnings}")
if failed > 0:
    print(f"❌ Failed:   {failed}")
else:
    print("❌ Failed:   0")

if failed == 0:
    print("\n🎉 ALL CRITICAL DEPENDENCIES VERIFIED!")
    print("The dashboard should be ready to run.")
    print("\nTo start the dashboard:")
    print("  streamlit run src/dashboard/app.py")
else:
    print(f"\n⚠️ {failed} CRITICAL ISSUES FOUND")
    print("Please install missing dependencies before running the dashboard.")

print("=" * 80)