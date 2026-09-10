#!/usr/bin/env python3
"""Patch SSL globally before importing Groq."""

import sys
import os
import ssl
import certifi

print("🔧 Patching SSL module globally...\n")

# CRITICAL: Patch create_default_context BEFORE importing httpx/groq
_original_create_default_context = ssl.create_default_context

def patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None):
    """Patched version that forces certifi bundle."""
    ctx = _original_create_default_context(purpose, cafile=certifi.where(), capath=capath, cadata=cadata)
    # Load additional certs from our bundle (includes Avast)
    ctx.load_verify_locations(cafile=certifi.where())
    return ctx

# Apply the patch
ssl.create_default_context = patched_create_default_context

print(f"✅ SSL patch applied")
print(f"   Certifi path: {certifi.where()}\n")

# NOW import Groq
print(f"📡 Importing Groq...")
from groq import Groq
from src.config.settings import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)
print(f"   ✅ Groq client created\n")

try:
    print(f"🧪 Making test API call...")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say: it works"}
        ],
        max_tokens=10,
        temperature=0,
        timeout=30.0
    )
    
    result = response.choices[0].message.content.strip()
    print(f"   ✅ SUCCESS!")
    print(f"   Response: '{result}'")
    sys.exit(0)
    
except Exception as e:
    print(f"   ❌ Failed: {type(e).__name__}: {e}")
    sys.exit(1)
