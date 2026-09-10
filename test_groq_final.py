#!/usr/bin/env python3
"""Final test of Groq API with proper SSL setup."""

import sys
import os
import certifi
import ssl
import urllib3

# Configure SSL for urllib3 (used by httpx/Groq)
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

print("🔧 SSL Configuration:")
print(f"   Certifi: {certifi.where()}")
print(f"   SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE')}")

# Suppress SSL warnings
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

from groq import Groq
from src.config.settings import GROQ_API_KEY

print(f"\n📡 Groq API Test:")
print(f"   Key length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0} chars")

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("   ✅ Client initialized")
    
    print("\n🧪 Making test API call (timeout=20s)...")
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say exactly: success"}
        ],
        max_tokens=10,
        temperature=0,
        timeout=20.0  # Explicit timeout
    )
    
    content = response.choices[0].message.content.strip()
    print(f"   ✅ API call successful!")
    print(f"   Response: '{content}'")
    print("\n✅ SUCCESS: Groq API is working!")
    sys.exit(0)
    
except Exception as e:
    print(f"   ❌ Error: {type(e).__name__}")
    print(f"   Message: {e}")
    
    # Check if it's a timeout
    if 'timeout' in str(e).lower() or 'timed out' in str(e).lower():
        print("\n⚠️  Timeout issue - Groq API may be slow or overloaded")
        print("   Try again in a moment")
    elif 'ssl' in str(e).lower() or 'certificate' in str(e).lower():
        print("\n❌ SSL/Certificate issue still present")
    elif 'connection' in str(e).lower():
        print("\n⚠️  Connection issue - may be network problem")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
