#!/usr/bin/env python3
"""Test Groq API with custom httpx client using updated certificates."""

import sys
import os
import certifi
import ssl
import httpx

print("🔧 Creating custom SSL context with Avast certificate...\n")

# Create SSL context that includes the Avast certificate
ssl_context = ssl.create_default_context(cafile=certifi.where())
# Important: Tell httpx to verify but use our context
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

print(f"   Certifi path: {certifi.where()}")
print(f"   SSL Context created")

# Create httpx client with custom SSL context
http_client = httpx.Client(verify=ssl_context)

print(f"\n📡 Creating Groq client with custom httpx client...")

from groq import Groq
from src.config.settings import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY, http_client=http_client)

print(f"   ✅ Groq client initialized\n")

try:
    print(f"🧪 Making test API call...")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say exactly: success"}
        ],
        max_tokens=10,
        temperature=0,
        timeout=30.0
    )
    
    content = response.choices[0].message.content.strip()
    print(f"   ✅ API call successful!")
    print(f"   Response: '{content}'")
    print(f"\n✅✅✅ SUCCESS: Groq API is working!")
    sys.exit(0)
    
except Exception as e:
    print(f"   ❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    http_client.close()
