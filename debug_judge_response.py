#!/usr/bin/env python3
"""Debug what the judge is actually returning."""

import sys
sys.path.insert(0, '.')

import json
import re
import time
import warnings
import httpx
from groq import Groq
from src.config.settings import GROQ_API_KEY

warnings.filterwarnings('ignore')
client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))

print("🧪 Testing judge response...\n")

prompt_systeme = (
    "Tu es un évaluateur. Tu réponds UNIQUEMENT "
    "en JSON valide, au format : "
    '{"note": <float 0-1>, "justification": "phrase"}'
)
prompt_utilisateur = """Évalue cette réponse: "Python est populaire".

Contexte: "Python est un langage populaire."

- note = 1.0 si soutenue
- note = 0.0 sinon"""

print("Sending judge request...")
try:
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": prompt_systeme},
            {"role": "user", "content": prompt_utilisateur},
        ],
        max_tokens=200,
        temperature=0,
        seed=42,
    )
    
    contenu = response.choices[0].message.content.strip()
    print(f"\n📝 RAW RESPONSE:")
    print(f"---")
    print(repr(contenu))
    print(f"---\n")
    
    print(f"First 200 chars: {contenu[:200]}\n")
    
    # Try stripping <think> tags
    contenu_stripped = re.sub(r"<think>.*?</think>", "", contenu, flags=re.DOTALL).strip()
    print(f"📝 AFTER <think> STRIP:")
    print(f"---")
    print(repr(contenu_stripped))
    print(f"---\n")
    
    # Try cleaning backticks
    contenu_final = re.sub(r"^```(?:json)?|```$", "", contenu_stripped, flags=re.MULTILINE).strip()
    print(f"📝 AFTER BACKTICK STRIP:")
    print(f"---")
    print(repr(contenu_final))
    print(f"---\n")
    
    # Try parsing
    try:
        result = json.loads(contenu_final)
        print(f"✅ JSON parsed successfully: {result}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse failed: {e}")
        print(f"   Trying regex fallback...")
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', contenu_final, re.DOTALL)
        if json_match:
            extracted = json_match.group(0)
            print(f"   Found: {repr(extracted)}")
            result = json.loads(extracted)
            print(f"   ✅ Parsed: {result}")
        else:
            print(f"   ❌ No JSON match found")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
