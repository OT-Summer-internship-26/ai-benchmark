# 🔧 Fix Terminal Errors - Step by Step

## ⚠️ Main Error Found
```
ModuleNotFoundError: No module named 'psycopg2'
```

This is the main issue. Let me help you fix it.

---

## ✅ SOLUTION: Install Missing Dependencies

### Step 1: Install psycopg2-binary NOW
```bash
pip install psycopg2-binary --upgrade
```

### Step 2: Verify Installation
```bash
python -c "import psycopg2; print('✓ psycopg2 installed')"
```

### Step 3: Install All Other Dependencies
```bash
# Install everything from requirements.txt
pip install -r requirements.txt --upgrade

# Then install these specific packages that often have issues:
pip install psycopg2-binary
pip install python-dotenv
pip install pydantic
pip install fastapi uvicorn
pip install pytest pytest-mock
```

### Step 4: Verify All Critical Imports
```bash
python -c "
import psycopg2
import fastapi
import sqlalchemy
import pydantic
import dotenv
import langchain
print('✓ ALL CRITICAL IMPORTS OK')
"
```

---

## 🧪 Test Each Fix

After each step, run these tests:

### Test 1: Check psycopg2
```bash
python -c "import psycopg2; print('✓ psycopg2 OK')"
```
**Expected:** `✓ psycopg2 OK`

### Test 2: Check API imports
```bash
python -c "from src.api.main import app; print('✓ API OK')"
```
**Expected:** `✓ API OK`

### Test 3: Check Database connection
```bash
python -c "
from src.database.connection import engine
print('✓ Database module loaded')
"
```
**Expected:** `✓ Database module loaded`

### Test 4: Run a unit test
```bash
python -m pytest tests/test_utils.py::TestEmailValidation::test_valid_email -v
```
**Expected:** `PASSED`

---

## 🚀 Once You Install psycopg2, Run This Complete Sequence

### Terminal 1: Start PostgreSQL (Keep Open)
```bash
docker run --name postgres-ooredoo ^
  -e POSTGRES_USER=ooredoo_user ^
  -e POSTGRES_PASSWORD=ooredoo_pass ^
  -e POSTGRES_DB=ai_benchmark ^
  -p 5432:5432 ^
  -d ankane/pgvector:latest

timeout /t 3

python -m src.database.init_db
```

### Terminal 2: Run All Tests
```bash
pytest tests/ -v
```

### Terminal 3: Start API (Keep Open)
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Terminal 4: Test Everything
```bash
# Test 1: Health Check
curl http://localhost:8000/

# Test 2: Register User
curl -X POST http://localhost:8000/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@test.com\",\"password\":\"Pass123\",\"role\":\"admin\"}"

# Test 3: Login
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@test.com\",\"password\":\"Pass123\"}"

# Test 4: Query Models
curl http://localhost:8000/benchmark/models

# Test 5: Query Scenarios  
curl http://localhost:8000/benchmark/scenarios
```

---

## 📋 Troubleshooting If Installation Fails

### Issue: "pip" command not found
```bash
# Use python module instead
python -m pip install psycopg2-binary --upgrade
```

### Issue: Permission denied
```bash
# Try with --user flag
pip install --user psycopg2-binary --upgrade
```

### Issue: Still getting psycopg2 error
```bash
# Completely uninstall and reinstall
pip uninstall psycopg2 psycopg2-binary -y
pip install psycopg2-binary --upgrade --force-reinstall
```

### Issue: Multiple Python versions
```bash
# Check which Python pip is using
pip --version

# Make sure it's Python 3.12
python --version

# If different, use full path
C:\Users\ranim\AppData\Local\Programs\Python\Python312\Scripts\pip.exe install psycopg2-binary --upgrade
```

---

## ✨ Complete Fix Script (Copy & Paste All)

```bash
# Step 1: Install psycopg2
pip install psycopg2-binary --upgrade

# Step 2: Verify
python -c "import psycopg2; print('✓ OK')"

# Step 3: Install all dependencies
pip install -r requirements.txt --upgrade
pip install psycopg2-binary python-dotenv pydantic fastapi uvicorn pytest pytest-mock --upgrade

# Step 4: Verify all imports
python -c "
import psycopg2
import fastapi
import sqlalchemy
import pydantic
print('✓ ALL OK')
"

# Step 5: Verify API loads
python -c "from src.api.main import app; print('✓ API OK')"

# Step 6: Run unit test
python -m pytest tests/test_utils.py::TestEmailValidation::test_valid_email -v

echo "✓ All fixes applied!"
```

---

## 🎯 What to Do Now

1. **FIRST**: Run the psycopg2 fix
   ```bash
   pip install psycopg2-binary --upgrade
   ```

2. **THEN**: Verify it works
   ```bash
   python -c "import psycopg2; print('✓ psycopg2 OK')"
   ```

3. **NEXT**: Follow the terminal setup instructions above

4. **FINALLY**: Run all component tests

---

## ✅ Success Indicators

Once fixed, you should see:
- ✅ No psycopg2 errors when importing API
- ✅ All unit tests pass
- ✅ API starts successfully
- ✅ Can register users
- ✅ Can login and get token
- ✅ Can query endpoints

---

**The fix is simple: `pip install psycopg2-binary --upgrade` - do this first!**

Then follow the complete sequence below to test everything.
