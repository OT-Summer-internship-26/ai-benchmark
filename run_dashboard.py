#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ooredoo IA Benchmark Dashboard Launcher

This is the recommended entry point for running the dashboard.
It handles path setup and launches the main app.

Usage:
    python run_dashboard.py
    
Or via Streamlit directly:
    streamlit run src/dashboard/admin_dashboard_page.py  (Admin dashboard)
    streamlit run src/dashboard/app.py                    (Full app with login)
    streamlit run src/dashboard/client_recommendation_page.py  (Client recommendations)
"""

import sys
import pathlib
import subprocess

# Get the project root (this file's directory)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent

# Ensure src is importable
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    print("Starting Ooredoo IA Benchmark Dashboard...")
    print(f"Project root: {PROJECT_ROOT}")
    
    # Run the main app with Streamlit
    app_path = PROJECT_ROOT / "src" / "dashboard" / "app.py"
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            cwd=str(PROJECT_ROOT),
            check=False
        )
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)
