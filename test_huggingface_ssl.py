#!/usr/bin/env python3
"""Test HuggingFace embedding model load - diagnose SSL failure."""

import sys
import os

print("🔍 Testing HuggingFace embedding model load (sentence-transformers)\n")

print("Step 1: Check environment variables")
print(f"  SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE', 'NOT SET')}")
print(f"  REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE', 'NOT SET')}")
print(f"  CURL_CA_BUNDLE: {os.environ.get('CURL_CA_BUNDLE', 'NOT SET')}\n")

print("Step 2: Try to import sentence_transformers")
try:
    from sentence_transformers import SentenceTransformer
    print("  ✅ Import successful\n")
except Exception as e:
    print(f"  ❌ Import failed: {e}\n")
    sys.exit(1)

print("Step 3: Try to load the model (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)")
print("  This will attempt to download from HuggingFace...\n")

try:
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print("  ✅ Model loaded successfully!")
    print(f"  Model type: {type(model)}")
    print(f"  Model name: {model.get_sentence_embedding_dimension()}-dim embeddings")
    
except Exception as e:
    print(f"  ❌ Model load failed!\n")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message:\n{str(e)}\n")
    
    import traceback
    print("Full traceback:")
    traceback.print_exc()
    
    sys.exit(1)
