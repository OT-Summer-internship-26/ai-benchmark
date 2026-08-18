# Model Coverage Report

**Status:** 4 of 12 models have benchmark data

---

## Models with Active Benchmarks ✅

| Model | Type | Executions | Modern Scores | Status |
|-------|------|-----------|----------------|--------|
| Llama 3.1 8B (Ollama) | Local | 26 | 47 | ✅ Primary |
| Mistral 7B (Ollama) | Local | 22 | 37 | ✅ Active |
| Gemma2 9B (Ollama) | Local | 4 | 9 | ✅ Limited |
| Qwen2.5 7B (Ollama) | Local | 4 | 6 | ✅ Limited |

**Total Active Scores:** 99 modern Ragas scores

---

## Models Pending Benchmarking ⏳

| Model | Type | Status |
|-------|------|--------|
| Claude 3.5 Sonnet | Remote (Anthropic) | ⏳ Not benchmarked |
| Gemini 1.5 Pro | Remote (Google) | ⏳ Not benchmarked |
| GPT-4o | Remote (OpenAI) | ⏳ Not benchmarked |
| GPT-4o-mini | Remote (OpenAI) | ⏳ Not benchmarked |
| Llama 3.1 8B Instant | Remote (Groq) | ⏳ Not benchmarked |
| Llama 3.3 70B | Remote (Groq) | ⏳ Not benchmarked |
| Mixtral 8x7B | Remote (Groq) | ⏳ Not benchmarked |
| Gemma2 9B | Remote | ⏳ Not benchmarked |

**Total Pending:** 8 remote models

---

## Score Distribution

```
Llama 3.1 8B (Ollama):  47 modern scores
Mistral 7B (Ollama):    37 modern scores
Gemma2 9B (Ollama):      9 modern scores
Qwen2.5 7B (Ollama):     6 modern scores
─────────────────────────────────
TOTAL:                   99 modern scores
                         90 legacy scores (archived)
```

---

## Dashboard Coverage

The admin dashboard currently shows:
- ✅ 4 models with actual benchmark data
- ✅ All 4 models have modern (is_legacy=FALSE) scores
- ✅ All queries correctly show only the 4 active models

The dashboard UI now clearly indicates **"4 of 12 models have data"** in the sidebar.

---

## Next Steps

To include remote models:
1. Set up API keys for Anthropic, OpenAI, Google, Groq
2. Run benchmarks with remote models
3. Models will automatically appear in leaderboard/radar once scores are recorded

---

**Verified:** 2026-08-14
**Query:** `SELECT m.nom, COUNT(DISTINCT e.id) FROM modeles m LEFT JOIN executions e ON e.modele_id = m.id GROUP BY m.nom ORDER BY COUNT DESC`
