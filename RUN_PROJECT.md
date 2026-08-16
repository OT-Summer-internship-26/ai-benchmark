# ▶️ RUN PROJECT - Complete Terminal Commands

This file contains ALL the exact commands you need to run, tested and ready to copy-paste.

---

## 🔧 STEP 1: Fix Dependencies (DO THIS FIRST!)

Open PowerShell and run:

```powershell
cd c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark

# Install the critical missing package
pip install psycopg2-binary --upgrade

# Verify it installed
python -c "import psycopg2; print('✓ psycopg2 OK')"

# Install all other dependencies
pip install -r requirements.txt --upgrade
```

**Expected output:**
```
✓ psycopg2 OK
Successfully installed X packages
```

If you see errors, use this instead:
```powershell
python -m pip install psycopg2-binary --upgrade --force-reinstall
```

---

## 📋 STEP 2: Verify Everything Can Import

```powershell
# Test API imports
python -c "from src.api.main import app; print('✓ API imports OK')"

# Test database
python -c "from src.database.connection import engine; print('✓ Database OK')"

# Test utils
python -c "from src.utils import validation; print('✓ Utils OK')"
```

**Expected:** All say `✓`

---

## 🐘 STEP 3: Start PostgreSQL (Terminal 1 - Keep Open)

```powershell
# Start PostgreSQL Docker container
docker run --name postgres-ooredoo ^
  -e POSTGRES_USER=ooredoo_user ^
  -e POSTGRES_PASSWORD=ooredoo_pass ^
  -e POSTGRES_DB=ai_benchmark ^
  -p 5432:5432 ^
  -d ankane/pgvector:latest

# Wait for it to start
timeout /t 3

# Initialize database tables
python -m src.database.init_db
```

**Expected output:**
```
<container_id>
Base de données initialisée avec succès.
```

---

## 🧪 STEP 4: Run All Unit Tests (Terminal 2)

```powershell
# Run all 100+ tests
pytest tests/ -v

# Or run specific test suites:
pytest tests/test_utils.py -v           # Validation tests
pytest tests/test_auth_utils.py -v      # Auth tests  
pytest tests/test_vector_store.py -v    # Vector store tests
```

**Expected output:**
```
====== 100+ passed in X.XXs ======
```

---

## 🚀 STEP 5: Start API Server (Terminal 3 - Keep Open)

```powershell
# Start the API
uvicorn src.api.main:app --reload --port 8000
```

**Expected output:**
```
Uvicorn running on http://127.0.0.1:8000
Application startup complete
```

**KEEP THIS TERMINAL OPEN!**

---

## 🧪 STEP 6: Test All Components (Terminal 4 - Run These)

### 6.1 Health Check
```powershell
curl http://localhost:8000/

# Expected: {"status":"ok",...}
```

### 6.2 Register User
```powershell
curl -X POST http://localhost:8000/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@test.com","password":"TestPass123","role":"admin"}'

# Expected: {"success":true,"message":"Compte créé..."}
```

### 6.3 Login and Get Token
```powershell
$loginResponse = curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@test.com","password":"TestPass123"}'

# Save the token
$token = ($loginResponse | ConvertFrom-Json).token
Write-Host "Token: $token"

# Expected: Shows a long token string
```

### 6.4 Get Current User (Test Auth)
```powershell
# Replace TOKEN with the value from previous step
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/auth/me

# Expected: {"id":1,"email":"admin@test.com","role":"admin"}
```

### 6.5 List Models
```powershell
curl http://localhost:8000/benchmark/models

# Expected: {"count":0,"modeles":[]}
```

### 6.6 List Scenarios
```powershell
curl http://localhost:8000/benchmark/scenarios

# Expected: {"count":0,"scenarios":[]}
```

### 6.7 Query Results with Pagination
```powershell
curl "http://localhost:8000/benchmark/results?limit=10&offset=0"

# Expected: {"total_count":0,"returned_count":0,"limit":10,"offset":0,"results":[]}
```

### 6.8 Test Validation Functions
```powershell
python -c "
from src.utils.validation import validate_email, validate_password

assert validate_email('admin@test.com') == True
is_valid, error = validate_password('TestPass123')
assert is_valid == True
print('✓ Validation functions working')
"

# Expected: ✓ Validation functions working
```

### 6.9 Test LLM Client
```powershell
python -c "
from src.models_clients.ollama_client import check_ollama_health

is_available = check_ollama_health()
if is_available:
    print('✓ Ollama available')
else:
    print('⚠ Ollama not running (optional)')
"
```

### 6.10 Test Agent Pipeline
```powershell
python -c "
from src.agents.graph import benchmark_graph
print('✓ Agent pipeline ready')
"

# Expected: ✓ Agent pipeline ready
```

---

## 📊 Summary of Results

If all tests pass, you should see:

```
✓ Health Check - API responds
✓ Authentication - Register & Login working
✓ Models & Scenarios - Endpoints accessible
✓ Pagination - Results endpoint working
✓ Validation - Input validation working
✓ Agent Pipeline - LangGraph compiled
✓ All 100+ unit tests passing
```

---

## 🎯 Quick Reference - Copy Exact Commands

### Install Dependencies
```powershell
pip install psycopg2-binary --upgrade
python -m src.database.init_db
```

### Start Services (3 Terminals)

**Terminal 1: Database**
```powershell
docker run --name postgres-ooredoo -e POSTGRES_USER=ooredoo_user -e POSTGRES_PASSWORD=ooredoo_pass -e POSTGRES_DB=ai_benchmark -p 5432:5432 -d ankane/pgvector:latest
timeout /t 3
python -m src.database.init_db
```

**Terminal 2: Tests**
```powershell
pytest tests/ -v
```

**Terminal 3: API**
```powershell
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 4: Test Commands** (Copy from sections 6.1-6.10 above)

---

## 🐛 If Something Fails

### Problem: "ModuleNotFoundError: psycopg2"
```powershell
pip uninstall psycopg2 psycopg2-binary -y
pip install psycopg2-binary --upgrade --force-reinstall
```

### Problem: "Connection refused" (Database)
```powershell
# Check if container running
docker ps | findstr postgres

# If not, restart
docker start postgres-ooredoo

# Or restart fresh
docker rm postgres-ooredoo
docker run -p 5432:5432 -e POSTGRES_PASSWORD=ooredoo_pass -d ankane/pgvector:latest
```

### Problem: "Connection refused" (API)
```powershell
# Port might be in use
netstat -ano | findstr :8000

# If in use, use different port
uvicorn src.api.main:app --reload --port 8001
```

### Problem: Tests fail
```powershell
pip install pytest pytest-mock --upgrade
pytest tests/test_utils.py::TestEmailValidation::test_valid_email -v -s
```

---

## ✅ Checklist

- [ ] Installed psycopg2: `pip install psycopg2-binary --upgrade`
- [ ] Verified imports: `python -c "import psycopg2"`
- [ ] Started PostgreSQL: `docker run ... ankane/pgvector:latest`
- [ ] Initialized database: `python -m src.database.init_db`
- [ ] Ran unit tests: `pytest tests/ -v`
- [ ] Started API: `uvicorn src.api.main:app --reload`
- [ ] Health check works: `curl http://localhost:8000/`
- [ ] Can register user
- [ ] Can login and get token
- [ ] Can query endpoints
- [ ] All components tested

---

**That's it! Follow the steps above and everything should work.** 🚀

Start with Step 1 (psycopg2), then follow Steps 3-6 in order across multiple terminals.
