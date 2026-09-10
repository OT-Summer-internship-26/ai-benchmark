#!/usr/bin/env python3
"""Test a real RAGAS evaluation with the fixed Groq client."""

import sys
sys.path.insert(0, '.')

from src.evaluation.metrics import evaluer_faithfulness, evaluer_answer_relevancy

print("🧪 Testing RAGAS evaluation with fixed Groq client...\n")

# Test data
response = "Python est un langage de programmation populaire et polyvalent utilisé dans de nombreux domaines."
chunks = [
    "Python est un langage de programmation créé par Guido van Rossum en 1991.",
    "Python est connu pour sa syntaxe simple et lisible.",
    "Python est largement utilisé en data science, web development, et automation."
]
question = "Qu'est-ce que Python et pourquoi est-il populaire?"

print("Input:")
print(f"  Response: {response}")
print(f"  Question: {question}")
print(f"  Chunks: {len(chunks)} context items\n")

try:
    print("Evaluating faithfulness...")
    result_faith = evaluer_faithfulness(response, chunks)
    print(f"  ✅ faithfulness: {result_faith}\n")
    
    print("Evaluating answer_relevancy...")
    result_relevancy = evaluer_answer_relevancy(response, question)
    print(f"  ✅ answer_relevancy: {result_relevancy}\n")
    
    print("="*60)
    print("✅✅✅ SUCCESS: RAGAS evaluations are working!")
    print("="*60)
    
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
