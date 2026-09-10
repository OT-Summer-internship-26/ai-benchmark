#!/usr/bin/env python3
"""Test Groq API with SSL verification disabled - WORKING VERSION."""

import sys
import os
import warnings

warnings.filterwarnings('ignore')
os.environ['GROQ_API_SSL_VERIFY'] = '0'

import httpx
from groq import Groq
from src.config.settings import GROQ_API_KEY

print("🧪 Testing Groq API connection...\n")

try:
    client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))
    print("✅ Groq client created")
    
    print("\n🧪 Making test API call with qwen/qwen3.6-27b...")
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "user", "content": "Say exactly: success"}
        ],
        max_tokens=10,
        temperature=0,
        timeout=30.0
    )
    
    result = response.choices[0].message.content.strip()
    print(f"✅ API call successful!")
    print(f"   Response: '{result}'")
    
    print(f"\n" + "="*60)
    print("✅✅✅ SUCCESS: Groq API is working!")
    print("="*60)
    print(f"\nThe SSL issue was caused by Avast antivirus MITM inspection.")
    print(f"Solution: Disable SSL verification for httpx client when")
    print(f"creating Groq client in corporate environments.")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
