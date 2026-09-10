#!/usr/bin/env python3
"""Test HuggingFace embedding model load after SSL fix."""

import sys
sys.path.insert(0, '.')

print("🧪 Testing HuggingFace embedding model with SSL fix\n")

try:
    from src.rag.embeddings import _get_model
    
    print("Loading embedding model...")
    model = _get_model()
    print(f"✅ Model loaded successfully!")
    print(f"   Model type: {type(model)}")
    print(f"   Embedding dim: {model.get_sentence_embedding_dimension()}\n")
    
    # Test getting an embedding
    test_text = "This is a test sentence for embedding"
    embedding = model.encode(test_text)
    print(f"✅ Encoding works!")
    print(f"   Text: '{test_text}'")
    print(f"   Embedding shape: {embedding.shape}")
    print(f"   First 5 dims: {embedding[:5]}\n")
    
    print("="*60)
    print("✅✅✅ SUCCESS: HuggingFace embedding model is working!")
    print("="*60)
    
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
