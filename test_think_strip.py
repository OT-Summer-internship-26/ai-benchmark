#!/usr/bin/env python3
"""Test the improved <think> tag stripping logic."""

import re
import json

# Sample response with unclosed <think> tag
raw_response = '''<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Evaluator
   - **Output Format:** Strictly JSON: `{"note": <float 0-1>, "justification": "phrase"}`

2.  **Determine Score:**
   note = 1.0 (fully supported)
</think>

{"note": 1.0, "justification": "Python is mentioned as popular in both"}'''

print("🧪 Testing <think> stripping logic\n")
print(f"Input:\n{repr(raw_response[:100])}...\n")

# Simulate the new logic
contenu = raw_response.strip()

if "<think>" in contenu:
    json_start = contenu.find("{")
    print(f"Found '<think>' at position 0")
    print(f"Found '{{' at position {json_start}\n")
    
    if json_start > 0:
        contenu = contenu[json_start:]  # Keep from { onwards
        print(f"✅ Extracted from {{ onwards:\n{repr(contenu)}\n")
    else:
        print("❌ No JSON found")

contenu = contenu.strip()
contenu_nettoye = re.sub(r"^```(?:json)?|```$", "", contenu, flags=re.MULTILINE).strip()

print(f"After cleanup:\n{repr(contenu_nettoye)}\n")

# Try parsing
try:
    result = json.loads(contenu_nettoye)
    print(f"✅ Successfully parsed JSON: {result}")
except json.JSONDecodeError as e:
    print(f"❌ JSON parse failed: {e}")
