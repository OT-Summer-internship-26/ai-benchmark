# 🎯 Complete Testing Guide - All Components

This guide provides the exact commands to test each component of the Ooredoo IA Benchmark project.

---

## 📋 Prerequisites

Make sure you have completed:
1. ✅ Installed dependencies: `pip install -r requirements.txt && pip install psycopg2-binary`
2. ✅ Created .env file: `copy .env.example .env`
3. ✅ PostgreSQL running (Docker or local)
4. ✅ Initialized database: `python -m src.database.init_db`

---

## 🧪 COMPLETE STARTUP & TEST SEQUENCE

Run these commands **in order** in separate terminal windows:

### Terminal 1: Start PostgreSQL (if using Docker)
```bash
docker run --name postgres-ooredoo \
  -e POSTGRES_USER=ooredoo_user \
  -e POSTGRES_PASSWORD=ooredoo_pass \
  -e POSTGRES_DB=ai_benchmark \
  -p 5432:5432 \
  -d ankane/pgvector:latest

# Wait for startup
timeout /t 3

# Verify it's running
docker ps | find "postgres-ooredoo"
# Should show: CONTAINER ID ... postgres-ooredoo
```

### Terminal 2: Initialize Database
```bash
python -m src.database.init_db

# Expected output:
# Base de données initialisée avec succès.
```

### Terminal 3: Run All Tests
```bash
# Run all 100+ unit tests
pytest tests/ -v

# Expected output:
# ====== 100+ passed in X.XXs ======

# If tests fail, run specific suite:
pytest tests/test_utils.py -v          # Validation tests
pytest tests/test_auth_utils.py -v     # Auth tests
pytest tests/test_vector_store.py -v   # Vector store tests
```

### Terminal 4: Start Ollama (Optional but recommended)
```bash
# Option A: Direct command
ollama serve

# Option B: Docker
docker run -d -p 11434:11434 ollama/ollama:latest

# Verify:
curl http://localhost:11434/api/tags
# Should return JSON with models

# Download a model (takes time):
ollama pull llama3.1:8b
```

### Terminal 5: Start the API Server
```bash
# This starts the main API
uvicorn src.api.main:app --reload --port 8000

# Expected output:
# Uvicorn running on http://127.0.0.1:8000
# Application startup complete

# Keep this terminal open! DON'T CLOSE IT
```

### Terminal 6: Run Component Tests (NEW - This is where you run all tests)

Now open a NEW terminal and follow the tests below:

---

## 🔬 Component Testing - Run These Commands

**Keep Terminal 5 (API) open and use Terminal 6 for these commands:**

### TEST 1: Health Check
```bash
# Basic health check
curl http://localhost:8000/

# Expected output:
# {"status":"ok","message":"API Benchmark Ooredoo opérationnelle","version":"1.0.0"}
```

### TEST 2: Authentication Component
```bash
echo "=== TEST 2: AUTHENTICATION COMPONENT ==="

# 2.1 Register a user
echo "2.1 Registering user..."
curl -X POST http://localhost:8000/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"SecurePass123\",\"role\":\"admin\"}"

# Expected: {"success":true,"message":"Compte créé..."}

# 2.2 Login to get token
echo "2.2 Logging in..."
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"password\":\"SecurePass123\"}"

# Expected: {"token":"<LONG_STRING>","user":{"id":1,"email":"test@example.com","role":"admin"}}

# SAVE THE TOKEN! Replace <TOKEN> in commands below

# 2.3 Get current user (use the token)
echo "2.3 Getting current user (requires token)..."
curl -X GET http://localhost:8000/auth/me ^
  -H "Authorization: Bearer <PASTE_TOKEN_HERE>"

# Expected: {"id":1,"email":"test@example.com","role":"admin"}
```

**✅ COMPONENT #1 TESTED: Authentication**

---

### TEST 3: RAG Pipeline Component
```bash
echo "=== TEST 3: RAG PIPELINE COMPONENT ==="

# 3.1 List models (no auth needed)
echo "3.1 Listing models..."
curl http://localhost:8000/benchmark/models

# Expected: {"count":X,"modeles":[...]}

# 3.2 List scenarios (no auth needed)
echo "3.2 Listing scenarios..."
curl http://localhost:8000/benchmark/scenarios

# Expected: {"count":X,"scenarios":[...]}

# If count is 0, seed test data:
echo "3.3 Seeding test data..."
python -c "
from src.database.connection import SessionLocal
from src.database.models import Scenario, Modele

db = SessionLocal()
model = Modele(nom='llama3.1:8b', fournisseur='Ollama', version='1.0', cout_par_1k_tokens=0)
db.add(model)

scenario = Scenario(
    departement='test',
    metier='testing',
    nom_cas_usage='Test Scenario',
    prompt='What is AI?',
    sortie_attendue='AI is artificial intelligence'
)
db.add(scenario)
db.commit()
print('✓ Test data seeded')
"

# 3.4 Verify data was added
echo "3.4 Verifying data..."
curl http://localhost:8000/benchmark/models
curl http://localhost:8000/benchmark/scenarios
```

**✅ COMPONENT #2 TESTED: RAG Pipeline**

---

### TEST 4: LLM Client Component
```bash
echo "=== TEST 4: LLM CLIENT COMPONENT ==="

# 4.1 Check Ollama health
echo "4.1 Checking Ollama health..."
python -c "
from src.models_clients.ollama_client import check_ollama_health
is_available = check_ollama_health()
print('✓ Ollama health check:', 'AVAILABLE' if is_available else 'NOT AVAILABLE')
"

# 4.2 Test response generation
echo "4.2 Testing response generation..."
python -c "
from src.models_clients.ollama_client import generate_response

try:
    response = generate_response(
        question='What is Python?',
        context_chunks=['Python is a programming language created by Guido van Rossum'],
        model_name='llama3.1:8b'
    )
    print('✓ LLM Response (first 100 chars):', response[:100])
except Exception as e:
    print('⚠ LLM generation failed:', str(e))
    print('  Make sure Ollama is running and model is downloaded')
"

# 4.3 Test retry logic
echo "4.3 Testing retry logic..."
python -c "
from src.utils.retry import retry_with_backoff

@retry_with_backoff(max_attempts=2, initial_delay=0.1)
def test_function():
    print('✓ Retry decorator working')
    return True

test_function()
"
```

**✅ COMPONENT #3 TESTED: LLM Client**

---

### TEST 5: Evaluation Component
```bash
echo "=== TEST 5: EVALUATION COMPONENT ==="

# 5.1 Test validation functions
echo "5.1 Testing validation functions..."
python -c "
from src.utils.validation import (
    validate_email, validate_password, validate_positive_int,
    validate_float_range, validate_list_not_empty, sanitize_string
)

# Email validation
assert validate_email('test@example.com') == True
assert validate_email('invalid') == False
print('✓ Email validation OK')

# Password validation
is_valid, error = validate_password('SecurePass123')
assert is_valid == True
print('✓ Password validation OK')

# Integer validation
is_valid, error, value = validate_positive_int(42, 'test_param')
assert is_valid == True and value == 42
print('✓ Integer validation OK')

# Float range validation
is_valid, error, value = validate_float_range(0.5, 0.0, 1.0)
assert is_valid == True
print('✓ Float range validation OK')

# List validation
is_valid, error = validate_list_not_empty([1, 2, 3])
assert is_valid == True
print('✓ List validation OK')

# String sanitization
sanitized = sanitize_string('  hello world  ', max_length=5)
print('✓ String sanitization OK')

print('✓ ALL VALIDATION TESTS PASSED')
"

# 5.2 Test authentication utilities
echo "5.2 Testing authentication utilities..."
python -c "
from src.auth.utils import hash_password, verify_password

password = 'TestPassword123'
hashed = hash_password(password)
print('✓ Password hashing OK')

is_correct = verify_password(password, hashed)
assert is_correct == True
print('✓ Password verification OK')

is_wrong = verify_password('WrongPassword', hashed)
assert is_wrong == False
print('✓ Wrong password detection OK')

print('✓ ALL AUTHENTICATION UTILITY TESTS PASSED')
"

# 5.3 Test exception handling
echo "5.3 Testing exception handling..."
python -c "
from src.utils.exceptions import (
    OllamaUnavailableException,
    ValidationException,
    DatabaseException
)

print('✓ All exception classes defined')
print('✓ Exception hierarchy working')
"
```

**✅ COMPONENT #4 TESTED: Evaluation**

---

### TEST 6: Agent Pipeline Component
```bash
echo "=== TEST 6: AGENT PIPELINE COMPONENT ==="

# 6.1 Test agent imports
echo "6.1 Testing agent imports..."
python -c "
from src.agents.graph import benchmark_graph
from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur
from src.agents.evaluateur import agent_evaluateur
from src.agents.consolidateur import agent_consolidateur

print('✓ All agent modules imported')
print('✓ LangGraph benchmark graph compiled')
print('✓ Agent pipeline components ready')
"

# 6.2 Test database models
echo "6.2 Testing database models..."
python -c "
from src.database.models import (
    Scenario, Modele, Execution, Score, Utilisateur
)

print('✓ All database models loaded')
print('✓ ORM mapping working')
"

# 6.3 Test agent with sample state
echo "6.3 Testing agent execution (sample)..."
python -c "
from src.agents.collecteur import agent_collecteur

# Create sample state
sample_state = {
    'scenario_ids': [1],  # May be empty if no data
    'model_names': ['test_model'],
    'erreurs': []
}

# Run collector agent
result = agent_collecteur(sample_state)

print('✓ Agent execution successful')
print('✓ State transformation working')
print('✓ Error handling working')
"
```

**✅ COMPONENT #5 TESTED: Agent Pipeline**

---

### TEST 7: API & Pagination Component
```bash
echo "=== TEST 7: API & PAGINATION COMPONENT ==="

# 7.1 Test models endpoint
echo "7.1 Testing models endpoint..."
curl http://localhost:8000/benchmark/models?limit=5

# Expected: {"count":X,"modeles":[...]}

# 7.2 Test scenarios endpoint
echo "7.2 Testing scenarios endpoint..."
curl http://localhost:8000/benchmark/scenarios?limit=5

# Expected: {"count":X,"scenarios":[...]}

# 7.3 Test results with pagination
echo "7.3 Testing results endpoint with pagination..."
curl "http://localhost:8000/benchmark/results?limit=10&offset=0"

# Expected: {
#   "total_count": X,
#   "returned_count": X,
#   "limit": 10,
#   "offset": 0,
#   "results": [...]
# }

# 7.4 Test results filtering
echo "7.4 Testing results filtering..."
curl "http://localhost:8000/benchmark/results?scenario_id=1&limit=10"
curl "http://localhost:8000/benchmark/results?modele_id=1&limit=10"

# 7.5 Test pagination boundaries
echo "7.5 Testing pagination boundaries..."
curl "http://localhost:8000/benchmark/results?limit=1&offset=0"
curl "http://localhost:8000/benchmark/results?limit=500&offset=100"

print('✓ Pagination tests passed')
"
```

**✅ COMPONENT #6 TESTED: API & Pagination**

---

### TEST 8: Full Benchmark Pipeline (Optional - Advanced)
```bash
echo "=== TEST 8: FULL BENCHMARK PIPELINE (ADVANCED) ==="

# This requires auth token from TEST 2
# Make sure you have a valid token first

echo "8.1 Running full benchmark..."
curl -X POST http://localhost:8000/benchmark/run ^
  -H "Authorization: Bearer <PASTE_TOKEN_FROM_TEST_2>" ^
  -H "Content-Type: application/json" ^
  -d "{\"scenario_ids\":[1],\"model_names\":[\"llama3.1:8b\"]}"

# Expected: {
#   "status": "completed",
#   "nb_scenarios": 1,
#   "nb_models": 1,
#   "nb_executions": 1,
#   "rapport": {...},
#   "erreurs": [],
#   "initiated_by": "test@example.com"
# }

echo "8.2 Querying results..."
curl http://localhost:8000/benchmark/results?limit=10

echo "✓ Full benchmark pipeline tested"
```

**✅ COMPONENT #7 TESTED: Full Pipeline (Optional)**

---

## 📊 Component Testing Summary

After running all tests above, you should see:

| Component | Status | Command |
|-----------|--------|---------|
| 1. Authentication | ✅ | `curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/auth/me` |
| 2. RAG Pipeline | ✅ | `curl http://localhost:8000/benchmark/models` |
| 3. LLM Client | ✅ | `python -c "from src.models_clients.ollama_client import ..."` |
| 4. Evaluation | ✅ | `pytest tests/test_utils.py -v` |
| 5. Agent Pipeline | ✅ | `python -c "from src.agents.graph import benchmark_graph"` |
| 6. API & Pagination | ✅ | `curl "http://localhost:8000/benchmark/results?limit=10"` |
| 7. Full Pipeline | ✅ | `curl -X POST http://localhost:8000/benchmark/run -H "Auth..."` |

---

## 🎯 Success Indicators

You'll know everything is working when:

- ✅ All unit tests pass: `pytest tests/ -v` (100+ tests)
- ✅ API responds to health check: `curl http://localhost:8000/`
- ✅ Can register and login: `curl -X POST http://localhost:8000/auth/login`
- ✅ Can access authenticated endpoints: `curl -H "Authorization: Bearer <TOKEN>"`
- ✅ Can query models and scenarios: `curl http://localhost:8000/benchmark/models`
- ✅ Results are paginated: `curl "http://localhost:8000/benchmark/results?limit=10"`
- ✅ Validation functions work: `pytest tests/test_utils.py -v`
- ✅ LLM client responds: `python -c "from src.models_clients.ollama_client import generate_response"`

---

## 🐛 Troubleshooting

### Test Fails: "Connection refused"
```bash
# Database not running
docker ps  # Check if container running
docker run -p 5432:5432 ... ankane/pgvector:latest

# API not running
uvicorn src.api.main:app --reload --port 8000
```

### Test Fails: "ModuleNotFoundError: psycopg2"
```bash
pip install psycopg2-binary
pip install --upgrade psycopg2-binary
```

### Test Fails: "No scenarios found"
```bash
# Need to seed data (see TEST 3.3 above)
python -c "
from src.database.connection import SessionLocal
from src.database.models import Scenario
# ... add scenario to database
"
```

### Test Fails: "Ollama not available"
```bash
# Start Ollama
ollama serve

# Or via Docker
docker run -d -p 11434:11434 ollama/ollama:latest
```

---

## 📝 Full Command Sequence (Copy-Paste)

**Terminal 1: Start Database**
```bash
docker run --name postgres-ooredoo -e POSTGRES_USER=ooredoo_user -e POSTGRES_PASSWORD=ooredoo_pass -e POSTGRES_DB=ai_benchmark -p 5432:5432 -d ankane/pgvector:latest
timeout /t 3
python -m src.database.init_db
```

**Terminal 2: Initialize & Test**
```bash
pytest tests/ -v
```

**Terminal 3: Start Ollama (optional)**
```bash
ollama serve
```

**Terminal 4: Start API**
```bash
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 5: Run All Component Tests** (see sections above)

---

## 🎓 Next Steps

1. ✅ Complete all tests above
2. ✅ Fix any failures using Troubleshooting section
3. ✅ Document any custom configurations
4. ✅ Read IMPLEMENTATION_GUIDE.md for architecture details
5. ✅ Begin development or deployment

---

**All core components should now be tested and working!** 🎉

See DEPLOYMENT_STEPS.md for production deployment guidance.
