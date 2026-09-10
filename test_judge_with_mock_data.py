#!/usr/bin/env python3
"""Test judge for context_precision/recall with mock data to see if judge itself works."""

import sys
sys.path.insert(0, '.')

from src.evaluation.metrics import evaluer_context_precision, evaluer_context_recall

print("🧪 Testing judge for context metrics with mock data\n")

# Mock data (simulating what would happen if RAG worked)
mock_chunks = [
    "Job description: Responsible for managing team communications and coordinating projects.",
    "Must have experience in organizational management and HR practices."
]

mock_question = "What are the key responsibilities for this HR position?"

mock_expected_output = "Strong leadership, team management skills, HR knowledge"

print("📝 Test Input:")
print(f"  Question: {mock_question}")
print(f"  Expected output: {mock_expected_output}")
print(f"  Chunks: {len(mock_chunks)} items\n")

# Test context_precision
print("Testing context_precision...")
try:
    result_precision = evaluer_context_precision(mock_chunks, mock_question)
    print(f"  ✅ Result: {result_precision}\n")
except Exception as e:
    print(f"  ❌ Error: {e}\n")

# Test context_recall
print("Testing context_recall...")
try:
    result_recall = evaluer_context_recall(mock_chunks, mock_expected_output)
    print(f"  ✅ Result: {result_recall}\n")
except Exception as e:
    print(f"  ❌ Error: {e}\n")

print("="*60)
print("Summary: If both judge calls work above, the judge itself is fine.")
print("Root cause of missing metrics is RAG search failure (HuggingFace SSL).")
print("="*60)
