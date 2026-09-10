#!/usr/bin/env python3
"""Test SSL fix by making a simple Groq API call."""

import sys
import os
import certifi

# Force Python to use certifi's certificate bundle
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['SSL_CERT_DIR'] = certifi.where()

print(f"🔧 SSL Configuration:")
print(f"   Certifi path: {certifi.where()}")
print(f"   SSL_CERT_FILE env: {os.environ.get('SSL_CERT_FILE')}")

# Now import and use Groq
from groq import Groq
from src.config.settings import GROQ_API_KEY

print(f"\n📡 Testing Groq API connection...")
print(f"   API Key present: {bool(GROQ_API_KEY)}")

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("   ✅ Groq client initialized")
    
    print(f"\n🧪 Attempting simple API call to llama-3.1-8b-instant...")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'hello' only, nothing else."}
        ],
        max_tokens=10,
        temperature=0
    )
    
    result = response.choices[0].message.content.strip()
    print(f"   ✅ API call successful!")
    print(f"   Response: '{result}'")
    
    if result.lower() == 'hello':
        print("\n✅ SUCCESS: SSL is fixed and Groq API is working!")
        sys.exit(0)
    else:
        print(f"\n⚠️  API responded but unexpected content: {result}")
        sys.exit(0)  # Still consider this a success since API call worked
        
except Exception as e:
    print(f"\n❌ FAILED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
