#!/usr/bin/env python3
"""Test Groq API with SSL verification disabled (temporary workaround for MITM inspection)."""

import sys
import os
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore')

# Disable SSL verification via environment variable (WARNING: Security risk, use only for testing)
os.environ['GROQ_API_SSL_VERIFY'] = '0'

# Monkey-patch httpx to disable SSL verification
import httpx

original_init = httpx.Client.__init__

def patched_init(self, *args, **kwargs):
    # Force verify=False for all connections
    kwargs['verify'] = False
    return original_init(self, *args, **kwargs)

httpx.Client.__init__ = patched_init

print("⚠️  WARNING: SSL verification is DISABLED for this test")
print("   This is a temporary workaround for Avast MITM inspection\n")

from groq import Groq
from src.config.settings import GROQ_API_KEY

print(f"📡 Creating Groq client with SSL verification disabled...")
client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))
print(f"   ✅ Groq client created\n")

try:
    print(f"🧪 Making test API call...")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say: working"}
        ],
        max_tokens=10,
        temperature=0,
        timeout=30.0
    )
    
    result = response.choices[0].message.content.strip()
    print(f"   ✅ API call SUCCESSFUL!")
    print(f"   Response: '{result}'")
    print(f"\n✅✅✅ SUCCESS: Groq API works without SSL verification!")
    print(f"\nℹ️  Next step: Apply this fix to src/evaluation/metrics.py")
    sys.exit(0)
    
except Exception as e:
    print(f"   ❌ Still failed: {type(e).__name__}: {e}")
    sys.exit(1)
