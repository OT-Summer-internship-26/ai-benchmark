# Gemini Backfill Blocked: SSL Certificate Verification Failure

## Issue Summary

Attempted to backfill RAGAS scores for 16 Gemini 3.1 Flash-Lite executions (IDs 74-89), but all API calls to Groq (the LLM judge service) are failing with SSL certificate verification errors.

## Root Cause

**Environment SSL Certificate Issue**

```
Error: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: 
       unable to get local issuer certificate (_ssl.c:1000)
```

This occurs when Python cannot verify SSL certificates for HTTPS connections. Causes:
- Missing or misconfigured SSL CA certificates on the system
- Python certificate store is outdated or empty
- Corporate firewall/proxy intercepting HTTPS
- SSL certificate chain incomplete

## Evidence

1. **Groq API connectivity test** (`test_groq_connectivity.py`):
   - ✅ Groq client initializes successfully
   - ✅ API key is valid (56 chars, properly set)
   - ❌ First API call fails with `APIConnectionError: Connection error`
   - Root cause in stack trace: `httpcore.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED]`

2. **Backfill attempt** (`scripts/re_evaluate_executions.py --apply`):
   - ✅ Database queries work
   - ✅ Scenario data loads successfully
   - ❌ LLM judge calls fail consistently:
     - Attempt 1/3: APIConnectionError - Connection error
     - Attempt 2/3: APIConnectionError - Connection error
     - Attempt 3/3: APIConnectionError - Connection error
   - Result: 0 scores inserted (all metrics returned None)

3. **Similar errors with HuggingFace**:
   - Embedding model download fails: `[SSL: CERTIFICATE_VERIFY_FAILED]`
   - But embedding model is cached, so RAG search fails gracefully

## Impact

❌ **Backfill BLOCKED**: Cannot evaluate the 16 Gemini executions
- 16 executions still have 0 scores
- Dashboard still shows None for all Gemini metrics

## Solutions

### Option A: Fix SSL Certificates (Recommended)

**On Windows:**

1. **Update Python certificates** (if using conda/venv):
   ```powershell
   # Find Python installation
   python -c "import certifi; print(certifi.where())"
   
   # Try to update certificates (requires pip)
   pip install --upgrade certifi
   ```

2. **Install system CA certificates** (requires admin):
   ```powershell
   # Using chocolatey (if installed)
   choco install -y ca-certificates
   
   # Or download latest CA bundle and configure Python to use it
   # See: https://pip.pypa.io/en/latest/user_guide/#ssl-certificate-verification
   ```

3. **Check if behind corporate proxy**:
   - If yes, configure pip/Python to use proxy:
     ```
     pip config set global.proxy [user:passwd@]proxy.server:port
     ```

### Option B: Disable SSL Verification (Not Recommended, Security Risk)

Only use this for testing/debugging in isolated environments:

```python
import ssl
import urllib3

# Disable SSL verification (UNSAFE - DO NOT USE IN PRODUCTION)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Or configure Groq client with verify=False
client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))
```

### Option C: Use Mock Scores (Testing Only)

For immediate dashboard testing without Groq API:

```python
# In re_evaluate_executions.py, add mock evaluation mode
if os.getenv("USE_MOCK_SCORES"):
    resultat = {
        "faithfulness": {"note": 0.85, "justification": "Mock score"},
        "answer_relevancy": {"note": 0.88, "justification": "Mock score"},
        "context_precision": {"note": 0.82, "justification": "Mock score"},
        "context_recall": {"note": 0.80, "justification": "Mock score"},
        "score_global": 0.84
    }
else:
    resultat = evaluer_execution_ragas(...)
```

## Recommended Next Steps

1. **Check system SSL configuration**:
   ```powershell
   # Test direct Python SSL
   python -c "import ssl; print(ssl.get_default_verify_paths())"
   ```

2. **Verify Python certificate store**:
   ```powershell
   python -c "import certifi; print(certifi.where())"
   ls (Get-Content (python -c "import certifi; print(certifi.where())"))
   ```

3. **If on corporate network**: Configure proxy in `.env` or system settings

4. **If in isolated environment**: Update SSL certificates via system package manager

## Temporary Workaround

Until SSL is fixed, you can manually insert mock scores for Gemini executions for dashboard testing:

```sql
INSERT INTO scores (execution_id, critere, note, commentaire) VALUES
-- Execution 74
(74, 'faithfulness', 0.85, 'Pending real evaluation'),
(74, 'answer_relevancy', 0.88, 'Pending real evaluation'),
(74, 'context_precision', 0.82, 'Pending real evaluation'),
(74, 'context_recall', 0.80, 'Pending real evaluation'),
(74, 'score_global', 0.84, 'Pending real evaluation'),
-- ... repeat for executions 75-89
```

## Status Summary

| Item | Status |
|------|--------|
| Execution data ready | ✅ 16/16 valid |
| Database connectivity | ✅ Working |
| Code logic | ✅ Correct |
| SSL certificates | ❌ BLOCKED |
| Backfill | ❌ BLOCKED |
| Dashboard display | ⏳ Waiting for scores |

---

**Action Required**: Fix SSL certificate verification on this system to unblock Groq API calls.
