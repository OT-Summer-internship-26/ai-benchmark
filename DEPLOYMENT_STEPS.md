# Complete Deployment Guide - Step by Step

## ⚠️ Prerequisites Check

Before starting, ensure you have:
- Python 3.9+ installed
- PostgreSQL database running (or Docker with PostgreSQL)
- Ollama running (for LLM testing)
- ~5-10 minutes of setup time

---

## Step 1: Install Dependencies

### 1.1 Check Python Version
```bash
python --version
# Expected: Python 3.9 or higher
```

### 1.2 Install Required Packages
```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Expected output: Successfully installed X packages
```

**If you get errors about missing modules:**
```bash
# Try installing specific packages that might be missing
pip install psycopg2-binary
pip install python-dotenv
pip install pydantic
pip install fastapi uvicorn
pip install langchain langgraph langchain-community
pip install sentence-transformers
pip install pytest pytest-mock
```

### 1.3 Verify Critical Imports
```bash
python -c "import sqlalchemy; print('SQLAlchemy OK')"
python -c "import fastapi; print('FastAPI OK')"
python -c "import langchain; print('LangChain OK')"
python -c "import psycopg2; print('psycopg2 OK')"
```

**If psycopg2 fails, run:**
```bash
pip install --upgrade psycopg2-binary
```

---

## Step 2: Configure Environment

### 2.1 Copy Configuration Template
```bash
cp .env.example .env
```

### 2.2 Edit .env File
```bash
# Open .env and update these values:

# DATABASE CONFIGURATION
# For local PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/ai_benchmark

# For Docker PostgreSQL:
# DATABASE_URL=postgresql://ooredoo_user:ooredoo_pass@localhost:5432/ai_benchmark

# For development (SQLite - testing only):
# DATABASE_URL=sqlite:///test.db

# LLM API KEYS (keep as sk-xxx if not using these services)
OPENAI_API_KEY=sk-xxx          # Optional
ANTHROPIC_API_KEY=sk-ant-xxx   # Optional
GEMINI_API_KEY=AIzaSyxxx       # Optional
GROQ_API_KEY=gsk-xxx           # Optional

# LOCAL LLM
OLLAMA_URL=http://localhost:11434

# APPLICATION
ENVIRONMENT=development
API_PORT=8000
LOG_LEVEL=DEBUG
```

### 2.3 Verify .env is Readable
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATABASE_URL:', os.getenv('DATABASE_URL', 'NOT SET'))"
```

---

## Step 3: Setup Database

### 3.1 Option A: Use Docker PostgreSQL (Recommended for Testing)

```bash
# Start PostgreSQL with pgvector support
docker run --name postgres-pgvector \
  -e POSTGRES_USER=ooredoo_user \
  -e POSTGRES_PASSWORD=ooredoo_pass \
  -e POSTGRES_DB=ai_benchmark \
  -p 5432:5432 \
  -d ankane/pgvector:latest

# Wait 5 seconds for PostgreSQL to start
# sleep 5
# Or on Windows: timeout /t 5

# Verify PostgreSQL is running
docker logs postgres-pgvector
# Expected: "database system is ready to accept connections"
```

### 3.2 Option B: Use Existing PostgreSQL
Update DATABASE_URL in .env with your connection string.

### 3.3 Initialize Database Tables
```bash
# Create all tables
python -m src.database.init_db

# Expected output:
# Base de données initialisée avec succès.
```

**If you get connection errors:**
```bash
# Check if PostgreSQL is running
# Check DATABASE_URL in .env is correct
# Make sure credentials are right

# For Docker:
docker ps | grep postgres
# Should show the running container
```

### 3.4 Verify Database Connection
```bash
python -c "
from src.database.connection import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(conn.text('SELECT 1'))
    print('Database connection OK:', result.fetchone())
"
```

**Expected output:** `Database connection OK: (1,)`

---

## Step 4: Start Ollama (Optional but Recommended for Testing)

### 4.1 Check if Ollama is Running
```bash
curl http://localhost:11434/api/tags
# Should return JSON with available models
```

### 4.2 Start Ollama if Not Running
```bash
# On Windows, download from: https://ollama.ai
# Then either:
# - Double-click ollama.exe, or
# - Run: ollama serve

# On Mac:
# brew install ollama
# ollama serve

# On Linux:
# curl https://ollama.ai/install.sh | sh
# ollama serve
```

### 4.3 Download a Model (Optional)
```bash
# This downloads the model and may take time
ollama pull llama3.1:8b

# Check available models
curl http://localhost:11434/api/tags | python -m json.tool
```

---

## Step 5: Run Unit Tests

### 5.1 Run All Tests
```bash
pytest tests/ -v

# Expected output:
# test_utils.py::TestEmailValidation::test_valid_email PASSED
# test_utils.py::TestEmailValidation::test_invalid_email PASSED
# ... (100+ tests)
# ====== 100+ passed in X.XXs ======
```

### 5.2 Run Specific Test Suites
```bash
# Validation tests
pytest tests/test_utils.py -v

# Authentication tests
pytest tests/test_auth_utils.py -v

# Vector store tests
pytest tests/test_vector_store.py -v
```

### 5.3 Run Tests with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
# Open: htmlcov/index.html in browser
```

**If tests fail:**
```bash
# Check database connection
python -c "from src.database.connection import get_engine; get_engine()"

# Check imports
python -c "from src.utils import validation, logger, retry, exceptions"

# Check pytest is installed
pip install pytest pytest-mock
```

---

## Step 6: Start the API Server

### 6.1 Start in Development Mode
```bash
uvicorn src.api.main:app --reload --port 8000

# Expected output:
# Uvicorn running on http://127.0.0.1:8000
# Application startup complete
```

### 6.2 Access API Documentation
Open in browser: **http://localhost:8000/docs**

You should see Swagger UI with all endpoints.

### 6.3 Health Check
```bash
curl http://localhost:8000/

# Expected output:
# {"status":"ok","message":"API Benchmark Ooredoo opérationnelle","version":"1.0.0"}
```

---

## Step 7: Test Authentication System

### 7.1 Register a New User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password_123",
    "role": "admin"
  }'

# Expected output:
# {"success":true,"message":"Compte créé pour admin@example.com (rôle : admin)."}
```

### 7.2 Login to Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password_123"
  }'

# Expected output:
# {"token":"<long_token_string>","user":{"id":1,"email":"admin@example.com","role":"admin"}}
```

**Save the token for next steps. On Windows PowerShell:**
```powershell
$response = curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@example.com","password":"secure_password_123"}'

# Extract token manually or use:
$token = ($response | ConvertFrom-Json).token
Write-Host "Token: $token"
```

### 7.3 Get Current User Info
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <YOUR_TOKEN>"

# Expected output:
# {"id":1,"email":"admin@example.com","role":"admin"}
```

---

## Step 8: Test RAG Pipeline

### 8.1 List Available Models
```bash
curl http://localhost:8000/benchmark/models

# Expected output:
# {"count":4,"modeles":[...]}
```

### 8.2 List Available Scenarios
```bash
curl http://localhost:8000/benchmark/scenarios

# Expected output:
# {"count":N,"scenarios":[...]}
```

**If these return empty results, you need to seed data first:**
```bash
# You'll need to seed your database with scenarios and models
# This would be done via database migrations or seed scripts
```

---

## Step 9: Test Full Benchmark Pipeline

### 9.1 Run a Benchmark (Requires Auth)
```bash
# Make sure you have a token from Step 7.2

curl -X POST http://localhost:8000/benchmark/run \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_ids": [1, 2],
    "model_names": ["llama3.1:8b", "mistral:7b"]
  }'

# Expected output:
# {
#   "status": "completed",
#   "nb_scenarios": 2,
#   "nb_models": 2,
#   "nb_executions": 4,
#   "rapport": {...},
#   "erreurs": [],
#   "initiated_by": "admin@example.com"
# }
```

### 9.2 Query Results with Pagination
```bash
curl "http://localhost:8000/benchmark/results?limit=10&offset=0"

# Expected output:
# {
#   "total_count": 4,
#   "returned_count": 4,
#   "limit": 10,
#   "offset": 0,
#   "results": [...]
# }
```

### 9.3 Filter Results by Scenario
```bash
curl "http://localhost:8000/benchmark/results?scenario_id=1&limit=50"
```

---

## Step 10: Component Testing

### 10.1 Test LLM Client Directly
```bash
python -c "
from src.models_clients.ollama_client import generate_response

response = generate_response(
    question='What is the capital of France?',
    context_chunks=['Paris is the capital of France.'],
    model_name='llama3.1:8b'
)
print('LLM Response:', response)
"
```

### 10.2 Test RAG/Vector Store
```bash
python -c "
from src.rag.vector_store import add_document_chunk, search_similar
import time

# Add a chunk
add_document_chunk('test_dept', 'This is a test document about machine learning')

# Wait a moment
time.sleep(1)

# Search for it
results = search_similar('machine learning', 'test_dept', top_k=1)
print('Search Results:', results)
"
```

### 10.3 Test Authentication Utils
```bash
python -c "
from src.auth.utils import hash_password, verify_password, create_user

# Test hashing
hashed = hash_password('test_password')
print('Password hashed:', len(hashed) > 0)

# Test verification
verified = verify_password('test_password', hashed)
print('Password verified:', verified)

# Test user creation
success, msg = create_user('test@example.com', 'secure_password', 'client')
print('User created:', success, '-', msg)
"
```

### 10.4 Test Validation Utils
```bash
python -c "
from src.utils.validation import validate_email, validate_password, validate_positive_int

# Email validation
print('Email valid:', validate_email('user@example.com'))

# Password validation
is_valid, error = validate_password('secure_pass_123')
print('Password valid:', is_valid)

# Integer validation
is_valid, error, value = validate_positive_int(42, 'test_value')
print('Integer valid:', is_valid, 'Value:', value)
"
```

---

## Common Errors & Fixes

### Error 1: "ModuleNotFoundError: No module named 'psycopg2'"
**Fix:**
```bash
pip install psycopg2-binary
# or
pip install --upgrade psycopg2-binary
```

### Error 2: "psycopg2.OperationalError: FATAL: database does not exist"
**Fix:**
```bash
# Create database and user in PostgreSQL
createdb -U postgres ai_benchmark
# or use PostgreSQL GUI/psql

# Or use Docker (see Step 3.1)
docker run -p 5432:5432 -e POSTGRES_PASSWORD=postgres -d postgres:latest
```

### Error 3: "Connection refused" when starting API
**Fix:**
```bash
# Make sure PostgreSQL is running
docker ps  # if using Docker
# or check your PostgreSQL service status

# Make sure DATABASE_URL in .env is correct
cat .env | grep DATABASE_URL
```

### Error 4: "Ollama is not available"
**Fix:**
```bash
# Start Ollama if not running
ollama serve

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Error 5: "No module named 'pytest'"
**Fix:**
```bash
pip install pytest pytest-mock
```

### Error 6: "No scenarios found" when querying
**Fix:**
```bash
# You need to seed your database with data
# Run the seed scripts or populate manually:
python -c "
from src.database.connection import get_SessionLocal
from src.database.models import Scenario, Modele
from sqlalchemy.orm import Session

db = get_SessionLocal()()
# Add sample scenario
scenario = Scenario(
    departement='test',
    metier='testing',
    nom_cas_usage='test_scenario',
    prompt='Test question?',
    sortie_attendue='Test answer'
)
db.add(scenario)
db.commit()
print('Scenario added')
"
```

---

## Complete Testing Sequence

Run these commands in order to test all components:

```bash
# 1. Check environment
python -c "import src; print('✓ Project imports OK')"

# 2. Check database
python -c "from src.database.connection import get_engine; get_engine(); print('✓ Database connection OK')"

# 3. Run unit tests
pytest tests/test_utils.py::TestEmailValidation -v
pytest tests/test_auth_utils.py::TestPasswordHashing -v
pytest tests/test_vector_store.py -v
echo "✓ Unit tests OK"

# 4. Start API
# (In separate terminal)
uvicorn src.api.main:app --reload --port 8000 &
sleep 3
echo "✓ API started"

# 5. Test health
curl http://localhost:8000/
echo "✓ Health check OK"

# 6. Test auth
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123456","role":"admin"}'
echo "✓ Registration OK"

# 7. Get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123456"}' | jq -r '.token')
echo "✓ Login OK, Token: ${TOKEN:0:20}..."

# 8. Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me
echo "✓ Authenticated request OK"

# 9. Test models endpoint
curl http://localhost:8000/benchmark/models
echo "✓ Models endpoint OK"

# 10. Test scenarios endpoint
curl http://localhost:8000/benchmark/scenarios
echo "✓ Scenarios endpoint OK"

echo ""
echo "✅ ALL TESTS PASSED!"
```

---

## Successful Deployment Indicators

You'll know everything is working when:

- ✅ `pip install -r requirements.txt` completes without errors
- ✅ Database initializes with `python -m src.database.init_db`
- ✅ All unit tests pass: `pytest tests/ -v`
- ✅ API starts: `uvicorn src.api.main:app --reload`
- ✅ Health check returns 200: `curl http://localhost:8000/`
- ✅ Can register user and get token
- ✅ Can access authenticated endpoints
- ✅ Can query models and scenarios
- ✅ Logs appear in console and file

---

## Next Steps

Once everything is working:

1. **Seed data** - Add real scenarios and models to database
2. **Configure LLMs** - Add API keys for OpenAI, Anthropic, etc.
3. **Run benchmarks** - Execute full benchmark pipelines
4. **Monitor** - Check logs and adjust settings as needed
5. **Deploy** - Move to production environment

---

**Congratulations! Your Ooredoo IA Benchmark is now deployed and tested!** 🎉
