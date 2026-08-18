#!/usr/bin/env python3
"""Test that all missing packages are now installed"""

import sys

print("Testing missing package imports...")
print()

try:
    import plotly.graph_objects as go
    print("[OK] plotly.graph_objects imported")
except Exception as e:
    print(f"[FAIL] plotly: {e}")
    sys.exit(1)

try:
    import requests
    print("[OK] requests imported")
except Exception as e:
    print(f"[FAIL] requests: {e}")
    sys.exit(1)

try:
    import pydantic
    print("[OK] pydantic imported")
except Exception as e:
    print(f"[FAIL] pydantic: {e}")
    sys.exit(1)

try:
    import transformers
    print("[OK] transformers imported")
except Exception as e:
    print(f"[FAIL] transformers: {e}")
    sys.exit(1)

print()
print("[SUCCESS] All 4 missing packages are now available")
print()
print("requirements.txt has been updated with:")
print("  - plotly")
print("  - requests")
print("  - pydantic")
print("  - transformers")
