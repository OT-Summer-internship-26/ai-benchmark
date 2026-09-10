#!/usr/bin/env python3
"""Test connectivity to Groq API."""

import sys
import os
from groq import Groq
from src.config.settings import GROQ_API_KEY

print("Testing Groq API connectivity...")
print(f"API Key present: {bool(GROQ_API_KEY)}")
print(f"API Key length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0}")

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq client initialized")
    
    print("\nAttempting simple API call...")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Say 'hello'"}
        ],
        max_tokens=10,
        temperature=0
    )
    print("✅ API call successful!")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ API call failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
