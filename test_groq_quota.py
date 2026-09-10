#!/usr/bin/env python3
"""Test if Groq quota has reset - minimal API call."""

import sys
sys.path.insert(0, '.')

import os
import warnings
warnings.filterwarnings('ignore')

# Ensure Groq client uses fixed SSL
import httpx
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

_original_httpx_client_init = httpx.Client.__init__

def _patched_httpx_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_httpx_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_httpx_client_init

from groq import Groq
from src.config.settings import GROQ_API_KEY

print("🧪 Testing Groq API quota status\n")

client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))

try:
    print("Sending minimal test call to Groq...")
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "user", "content": "Reply with: ok"}
        ],
        max_tokens=5,
        temperature=0
    )
    
    result = response.choices[0].message.content.strip()
    print(f"✅ SUCCESS! Groq API is responding")
    print(f"   Response: '{result}'")
    print(f"\n✅ QUOTA RESET - Ready to continue\n")
    
except Exception as e:
    if "429" in str(e) or "rate_limit" in str(e).lower():
        print(f"❌ RATE LIMIT STILL ACTIVE")
        print(f"   Error: {e}\n")
        print("   Quota has NOT reset yet. Please wait and retry in a few minutes.\n")
        sys.exit(1)
    else:
        print(f"❌ Different error: {type(e).__name__}: {e}\n")
        sys.exit(1)
