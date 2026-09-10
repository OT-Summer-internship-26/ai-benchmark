# Context Metrics Root Cause Table

## Summary

| execution_id | model | metric | root_cause |
|---|---|---|---|
| 4 | Qwen2.5 7B (Ollama) | context_precision | rag_search_error (HuggingFace SSL) |
| 4 | Qwen2.5 7B (Ollama) | context_recall | rag_search_error (HuggingFace SSL) |
| 8 | Qwen2.5 7B (Ollama) | context_precision | rag_search_error (HuggingFace SSL) |
| 8 | Qwen2.5 7B (Ollama) | context_recall | rag_search_error (HuggingFace SSL) |
| 12 | Qwen2.5 7B (Ollama) | context_precision | rag_search_error (HuggingFace SSL) |
| 12 | Qwen2.5 7B (Ollama) | context_recall | rag_search_error (HuggingFace SSL) |
| 16 | Qwen2.5 7B (Ollama) | context_precision | rag_search_error (HuggingFace SSL) |
| 16 | Qwen2.5 7B (Ollama) | context_recall | rag_search_error (HuggingFace SSL) |

## Key Findings

- **Gemma2 9B**: No executions found in database
- **All 8 missing metrics**: Caused by same root cause — RAG search SSL failure
- **Sortie_attendue**: Present for all 4 executions (context_recall=None is NOT due to missing expected output)
- **Judge**: Verified working correctly with mock data (context_precision=0.5, context_recall=0.8)
- **Error details**: `[SSL: CERTIFICATE_VERIFY_FAILED]` from HuggingFace embedding model download

## Cause Classification

### ✅ NOT Root Causes
- Empty sortie_attendue (expected output) → All present
- Judge API failure → Judge tested and works
- Code bug in metrics.py → Judge logic is correct
- Code bug in RAG layer → Exception handling is correct

### ❌ ROOT CAUSE
- **HuggingFace SSL Certificate Verification Failure**
  - Cannot download sentence-transformer model (paraphrase-multilingual-MiniLM-L12-v2)
  - RAG search returns empty chunks
  - Judge correctly returns None for context metrics (cannot evaluate empty context)

## Comparison: Expected Behavior

When RAG search fails and returns 0 chunks:

| Metric | With Empty Chunks | Status |
|--------|-------------------|--------|
| faithfulness | May score (depends on implementation) | Returned scores for some |
| answer_relevancy | May score (doesn't require context) | Returned scores |
| **context_precision** | **None (correct - needs chunks)** | **None ✓** |
| **context_recall** | **None (correct - needs chunks)** | **None ✓** |

**Conclusion**: The None values are the CORRECT behavior, not a bug.

