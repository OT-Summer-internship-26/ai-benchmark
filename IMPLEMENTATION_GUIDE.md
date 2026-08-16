# Implementation Guide - Ooredoo IA Benchmark Fixes

## Quick Start

### 1. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env and add your API keys and database URL
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python -m src.database.init_db
```

### 4. Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_utils.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### 5. Start API Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

### 6. Access API Documentation
Open browser: `http://localhost:8000/docs`

---

## Key Changes by Category

### Security Improvements

#### 1. Input Validation
**Location**: `src/utils/validation.py`

```python
from src.utils.validation import (
    validate_email,
    validate_password,
    validate_positive_int,
    validate_float_range,
    validate_list_not_empty,
    sanitize_string
)

# Email validation
is_valid = validate_email("user@example.com")

# Password validation
is_valid, error = validate_password("secure_pass_123")

# Integer validation
is_valid, error, value = validate_positive_int(42, "my_param")
```

#### 2. Authentication & Authorization
**Location**: `src/api/auth.py`, `src/api/routes/auth.py`

```python
# Login
POST /auth/login
{
    "email": "user@example.com",
    "password": "password"
}
# Returns: {"token": "...", "user": {...}}

# Register
POST /auth/register
{
    "email": "newuser@example.com",
    "password": "secure_password",
    "role": "client"  # or "admin", "super_admin"
}

# Get Current User
GET /auth/me
Headers: Authorization: Bearer <token>
```

#### 3. Protected Endpoints
**Location**: `src/api/routes/benchmark.py`

```python
# Requires admin or super_admin role
POST /benchmark/run
Headers: Authorization: Bearer <token>
{
    "scenario_ids": [1, 2, 3],
    "model_names": ["llama3.1:8b", "mistral:7b"]
}
```

### Reliability Improvements

#### 1. Retry Logic with Exponential Backoff
**Location**: `src/utils/retry.py`

```python
from src.utils.retry import retry_with_backoff

@retry_with_backoff(
    max_attempts=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
def unstable_operation():
    # This will retry up to 3 times with exponential backoff
    pass
```

#### 2. Ollama Health Checks
**Location**: `src/models_clients/ollama_client.py`

```python
from src.models_clients.ollama_client import check_ollama_health, generate_response

# Check if Ollama is available before running
if not check_ollama_health():
    raise OllamaUnavailableException("Ollama is not running")

# generate_response now has built-in retry logic
response = generate_response(
    question="What is the policy?",
    context_chunks=["..."],
    model_name="llama3.1:8b"
)
```

#### 3. Proper Error Handling
**Location**: `src/utils/exceptions.py`

```python
from src.utils.exceptions import (
    OllamaUnavailableException,
    LLMException,
    DatabaseException,
    ValidationException
)

try:
    response = generate_response(...)
except OllamaUnavailableException:
    # Handle Ollama not running
    logger.error("Ollama service unavailable")
except LLMException as e:
    # Handle LLM-specific errors
    logger.error(f"LLM error: {e}")
```

### Database Improvements

#### 1. Connection Pooling
**Location**: `src/database/connection.py`

```python
# Configured with:
# - pool_size=10 (maintain 10 connections)
# - max_overflow=20 (allow up to 20 overflow connections)
# - pool_pre_ping=True (test connections before use)
# - pool_recycle=3600 (recycle after 1 hour)
```

#### 2. Proper Transaction Management
**Location**: All agent files

```python
# Before (problematic):
with engine.connect() as conn:
    conn.execute(...)
    conn.commit()  # Manual commit

# After (fixed):
with engine.begin() as conn:  # Automatic transaction
    conn.execute(...)
    # Auto-commit on success, auto-rollback on error
```

#### 3. Vector Store Fixes
**Location**: `src/rag/vector_store.py`

```python
# Before (broken):
embedding_str = str(embedding)  # Produces: "[0.1, 0.2, ...]"

# After (correct for pgvector):
embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'  # "[0.1,0.2,...]"

# Usage in SQL:
result = conn.execute(
    text("... embedding::vector ..."),
    {"embedding": embedding_str}
)
```

### Logging Improvements

#### 1. Structured Logging
**Location**: `src/utils/logger.py`

```python
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Now logs are structured with:
# - Timestamps
# - Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
# - Module names
# - Rotating file handler (10MB max, 5 backups)

logger.debug("Detailed debug info")
logger.info("Important operation started")
logger.warning("Potential issue")
logger.error("Error occurred")
logger.critical("System failure")
```

### API Improvements

#### 1. Input Validation with Pydantic
**Location**: `src/api/models.py`

```python
from pydantic import BaseModel, Field

class BenchmarkRunRequest(BaseModel):
    scenario_ids: List[int] = Field(..., min_items=1)
    model_names: List[str] = Field(..., min_items=1)
    
    @field_validator('scenario_ids')
    @classmethod
    def validate_scenario_ids(cls, v):
        if not all(isinstance(x, int) and x > 0 for x in v):
            raise ValueError("All scenario IDs must be positive integers")
        return v
```

#### 2. Pagination
**Location**: `src/api/routes/results.py`

```python
# GET /benchmark/results?limit=50&offset=0&scenario_id=1&modele_id=2

# Returns:
{
    "total_count": 1000,        # Total before pagination
    "returned_count": 50,       # Actual returned
    "limit": 50,
    "offset": 0,
    "results": [...]
}
```

---

## Testing

### Unit Tests Structure

```
tests/
├── test_utils.py           # 60+ tests for validation functions
├── test_auth_utils.py      # 30+ tests for authentication
├── test_vector_store.py    # 15+ tests for RAG operations
└── test_*.py              # Existing tests
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test class
pytest tests/test_utils.py::TestEmailValidation -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
# Open: htmlcov/index.html
```

### Example Test

```python
def test_email_validation():
    assert validate_email("user@example.com") is True
    assert validate_email("invalid") is False
```

---

## Configuration

### Environment Variables

See `.env.example` for all available options:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk-...

# Local LLM
OLLAMA_URL=http://localhost:11434

# Application
ENVIRONMENT=development
API_PORT=8000
LOG_LEVEL=INFO

# Features
ENABLE_OLLAMA=true
ENABLE_OPENAI=true
```

---

## Workflow Examples

### 1. Running a Benchmark (with Auth)

```bash
# Step 1: Register user (if not exists)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password",
    "role": "admin"
  }'

# Step 2: Login to get token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password"
  }' | jq -r '.token')

# Step 3: Run benchmark with token
curl -X POST http://localhost:8000/benchmark/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": [1, 2, 3],
    "model_names": ["llama3.1:8b", "mistral:7b"]
  }'
```

### 2. Querying Results with Pagination

```bash
# Get first 50 results
curl http://localhost:8000/benchmark/results?limit=50&offset=0

# Get next page
curl http://localhost:8000/benchmark/results?limit=50&offset=50

# Filter by scenario
curl http://localhost:8000/benchmark/results?scenario_id=1&limit=50

# Filter by model
curl http://localhost:8000/benchmark/results?modele_id=9&limit=50
```

---

## Common Issues & Solutions

### Issue: Connection Pool Exhausted
**Symptoms**: "QueuePool limit exceeded"

**Solution**:
```python
# Ensure all database operations use context managers
with engine.connect() as conn:
    # Code here
# Auto-cleanup on exit
```

### Issue: Ollama Not Responding
**Symptoms**: "Ollama is not available"

**Solution**:
```bash
# Start Ollama
ollama serve

# Then verify
curl http://localhost:11434/api/tags
```

### Issue: Invalid Embedding Format
**Symptoms**: "psycopg2.errors.DataError"

**Solution**:
```python
# Check embedding format is correct
embedding = [0.1, 0.2, 0.3]
embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
# Result: '[0.1,0.2,0.3]'
```

---

## Performance Tuning

### Database Connection Pool
```python
# Increase for high concurrency
pool_size=20         # Default: 10
max_overflow=50      # Default: 20
pool_pre_ping=True   # Always enabled (best practice)
```

### LLM Retry Settings
```python
@retry_with_backoff(
    max_attempts=5,           # More retries for unstable networks
    initial_delay=2.0,        # Longer initial wait
    backoff_factor=2.0,       # Standard exponential backoff
    max_delay=120.0,          # Cap at 2 minutes
)
```

### Logging Level
```env
# Production
LOG_LEVEL=WARNING

# Development
LOG_LEVEL=DEBUG
```

---

## Deployment Checklist

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in all required API keys in `.env`
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Run `python -m src.database.init_db`
- [ ] Run tests: `pytest tests/`
- [ ] Configure database backups
- [ ] Enable HTTPS in production
- [ ] Set up monitoring/alerting
- [ ] Review and update CORS settings if needed
- [ ] Generate strong `JWT_SECRET_KEY`
- [ ] Set up log aggregation (optional)

---

## Support & Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Code Docs**: See docstrings in each module
- **Issues**: Check logs in `logs/benchmark.log`
- **Tests**: See `tests/` directory for usage examples

---

## Next Steps

1. Review `FIXES_SUMMARY.md` for detailed change list
2. Run unit tests to verify your setup
3. Start the API and test authentication
4. Run a benchmark with the new authenticated endpoints
5. Monitor logs for any issues

---

**Version**: 1.0.0  
**Last Updated**: August 2026  
**Status**: Production Ready
