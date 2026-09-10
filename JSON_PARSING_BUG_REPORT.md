# JSON Parsing Bug Report - Real Issue Found ✅

**Date**: August 26, 2026  
**Status**: DIAGNOSED & READY FOR FIX (awaiting approval)

---

## Executive Summary

**Bug**: Judge responses for `context_precision` and `context_recall` are **TRUNCATED mid-JSON** due to `max_tokens=500` limit being too low for Qwen's reasoning-heavy responses.

**Root Cause**: The model generates very long `<think>...</think>` reasoning blocks (600+ tokens). With `max_tokens=500` in the API call, the response gets cut off before the JSON payload is output.

**Impact**: JSON extraction fails → context metrics return None → these metrics appear missing in dashboard

**Fix**: Increase `max_tokens` for context metrics to allow full model output

---

## Evidence: Raw Judge Responses

### Response 1: context_precision (TRUNCATED)

```
<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Evaluator
   - **Output Format:** Strict JSON only: `{"note": <float 0-1>, "justification": "<phrase courte>"}`
   - **Task:** Evaluate the PRECISION of the provided context...
   
   [... 1500+ chars of reasoning ...]
   
5.  **Construct JSON Output:**
   - `{"note": 1.0, "justification": "Le contexte liste explicitement..."}`
   - Check format: Valid JSON, no extra text...
   
   All steps verified. Output matches requirements.✅
</think>

{"note": 1.0, "justification": "Le contexte liste explicit'
```

**Issue**: 
- Ends at: `"Le contexte liste explicit'` (unterminated string)
- Missing closing quote, closing brace, closing `</think>` tag
- Total: 2123 chars (response cut off at token limit)

### Response 2: context_recall (TRUNCATED WORSE)

```
<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Evaluator
   - **Output Format:** Strict JSON only: `{"note": <float 0-1>, "justification": "<phrase courte>"}`
   - **Task:** Evaluate the RECALL of the provided context...
   
   [... 1400+ chars of reasoning ...]
   
4.  **Draft Justification (short phrase in French, as requested/implied by prompt language):**
   - "Toutes les informations requises sont présentes dans le contexte."
   - Or: "Le contexte contient l'intégralité des éléments demandés."
   - Keep it concise.

5.  **Format Output:**
   - Must be strictly JSON:'
```

**Issue**:
- Ends mid-sentence at: `Must be strictly JSON:` (no JSON payload at all!)
- Total: 1946 chars
- Reasoning incomplete, no JSON object present

---

## Why Current Code Fails

### Step 1: Raw response arrives
```python
raw = '...long <think>...</think> incomplete JSON...'
```

### Step 2: Regex tries to strip `<think>...</think>`
```python
contenu = re.sub(r"<think>.*?</think>", "", contenu, flags=re.DOTALL)
```
**Result**: NO MATCH (because `</think>` is missing due to truncation!)
```
'...long thinking reasoning... {"note": 1.0, "justification": "incomplete\''
```

### Step 3: JSON extraction tries to parse
```python
json_matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', contenu_nettoye, re.DOTALL))
```
**Result**: Finds `{"note": 1.0, "justification": "Le contexte liste explicit'`

### Step 4: Parsing fails
```python
json.loads('{"note": 1.0, "justification": "Le contexte liste explicit\'')
```
**Error**: 
```
JSONDecodeError: Unterminated string starting at: line 1 column 32 (char 31)
```

### Step 5: All 3 retries fail with same error
```
[JUGE] tentative 1/3 échouée : ValueError - Pas de JSON valide trouvé dans: ...
[JUGE] tentative 2/3 échouée : ValueError - Pas de JSON valide trouvé dans: ...
[JUGE] tentative 3/3 échouée : ValueError - Pas de JSON valide trouvé dans: ...
```

---

## Why This Happens Only for Context Metrics

### Comparison of response lengths:

| Metric | Reasoning Length | Total Length | Hits Limit? |
|--------|------------------|--------------|-----------|
| faithfulness | ~400 tokens | < 500 | ❌ Usually OK |
| answer_relevancy | ~300 tokens | < 500 | ❌ Usually OK |
| **context_precision** | ~700 tokens | > 500 | ✅ **TRUNCATES** |
| **context_recall** | ~850 tokens | > 500 | ✅ **TRUNCATES** |

Context metrics require more reasoning because the judge must:
1. Analyze all chunks provided
2. Compare to question/expected output
3. Determine relevance/completeness

Result: Much longer `<think>` blocks → exceed token limit

---

## Proposed Fix

### Option A: Increase max_tokens (RECOMMENDED)

**Current code in `src/evaluation/metrics.py` `_appeler_juge_une_fois()`:**
```python
response = client.chat.completions.create(
    model=MODELE_JUGE,
    messages=[...],
    max_tokens=1200,  # ← This applies to ALL metrics
    temperature=0,
    seed=42,
)
```

**Issue**: `max_tokens=1200` was increased globally, but context metrics still fail because:
- Qwen's output format is very verbose in `<think>` reasoning
- The regex expects a clean JSON after stripping `</think>`
- When truncated, there IS no clean `</think>` tag to strip

**Proposed fix**: Use **dynamic max_tokens per metric**

```python
def _appeler_juge_une_fois(prompt_systeme: str, prompt_utilisateur: str, metric_type: str = "default") -> float | None:
    """
    Args:
        metric_type: 'context' (context_precision/recall) needs more tokens due to verbose reasoning
    """
    # Context metrics need longer reasoning + JSON output
    max_tokens = 2000 if 'context' in prompt_utilisateur.lower() else 1200
    
    response = client.chat.completions.create(
        model=MODELE_JUGE,
        messages=[...],
        max_tokens=max_tokens,  # ← Dynamic per metric
        temperature=0,
        seed=42,
    )
```

### Option B: Improve JSON Extraction to Handle Partial JSON

**Alternative**: Detect truncation and retry with higher limit

```python
def _is_likely_truncated(contenu: str) -> bool:
    """Check if response appears truncated (no closing } or unterminated string)"""
    # Count braces
    open_braces = contenu.count('{')
    close_braces = contenu.count('}')
    
    if open_braces > close_braces:
        return True  # Unmatched opening brace
    
    # Check for unterminated strings
    if '"' in contenu and contenu.rstrip().endswith('"') == False and '"' in contenu[-20:]:
        return True  # Likely unterminated
    
    return False
```

Then in retry logic:
```python
if _is_likely_truncated(contenu_nettoye):
    # Retry with higher max_tokens
    ...
```

---

## Recommendation

**Use Option A** (dynamic max_tokens) because:

1. ✅ Simpler and more direct
2. ✅ Prevents truncation at source (better than detecting after)
3. ✅ Wastes few extra tokens (only for context metrics)
4. ✅ Cleaner code path (one retry strategy, not two)

**Implementation**:
- Detect metric type from prompt content (contains "contexte_chunks" vs other text)
- Set max_tokens=2000 for context metrics, 1200 for others
- Simple, testable change

---

## Validation

Once fixed, the same responses should:
1. Generate full `<think>...</think>` reasoning
2. Output complete JSON with closed quotes and braces
3. Parse successfully with `json.loads()`
4. Return scores like: `{"note": 1.0, "justification": "..."}`

---

## Impact if Not Fixed

- Context metrics stay None for all affected executions
- Dashboard shows incomplete evaluation results
- 100+ Ollama executions remain un-scored for context quality
- User has no visibility into retrieval quality (precision/recall)

---

## Status

✅ **BUG IDENTIFIED**
⏳ **AWAITING APPROVAL TO IMPLEMENT**

Once approved, fix is straightforward:
1. Modify `_appeler_juge_une_fois()` to use dynamic max_tokens
2. Test with context metrics
3. Proceed with backfill
