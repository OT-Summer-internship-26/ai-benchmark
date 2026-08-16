# 🎯 START HERE - Ooredoo IA Benchmark

Welcome! This document guides you through getting the project up and running.

---

## 📋 What You Need

Before starting, make sure you have:
- **Python 3.9+** installed
- **Git** (optional, for version control)
- **Docker** (optional, for PostgreSQL)
- **~15 minutes** of setup time

---

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt --upgrade
pip install psycopg2-binary  # Critical!
```

### 2. Setup Database
**Option A: Docker (Easiest)**
```bash
docker run --name postgres-ooredoo \
  -e POSTGRES_USER=ooredoo_user \
  -e POSTGRES_PASSWORD=ooredoo_pass \
  -e POSTGRES_DB=ai_benchmark \
  -p 5432:5432 \
  -d ankane/pgvector:latest

# Wait 5 seconds
timeout /t 5

# Initialize tables
python -m src.database.init_db
```

**Option B: Existing PostgreSQL**
```bash
# Edit .env and set DATABASE_URL to your connection string
# Then initialize tables
python -m src.database.init_db
```

### 3. Run Tests
```bash
pytest tests/ -v
# Expected: 100+ tests pass ✓
```

### 4. Start API
```bash
uvicorn src.api.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```

### 5. Test Authentication
```bash
# In new terminal:
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Pass123","role":"admin"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Pass123"}'
# Copy the returned token for next steps
```

---

## 📚 Documentation Guide

Choose your next step based on what you need:

### 🔧 **Setup & Deployment**
- **NEW TO PROJECT?** → Read `STARTUP_GUIDE.md` (step-by-step setup)
- **NEED DETAILED STEPS?** → Read `DEPLOYMENT_STEPS.md` (comprehensive guide)
- **QUICK CHECKLIST?** → See `VERIFICATION_CHECKLIST.md` (what was fixed)

### 🔍 **Understanding the Code**
- **WHAT WAS FIXED?** → Read `FIXES_SUMMARY.md` (all 15 fixes explained)
- **HOW DOES IT WORK?** → Read `IMPLEMENTATION_GUIDE.md` (technical details)
- **EXAMPLES?** → Check the README files in src/ directories

### 🧪 **Testing & Verification**
- **RUN TESTS:** `pytest tests/ -v`
- **VERIFY SETUP:** See STARTUP_GUIDE.md Step 5
- **TEST COMPONENTS:** See sections below

---

## ✅ Component Testing Checklist

After setup, test each component:

### 1️⃣ Authentication (Core Component)
```bash
# Step 1: Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Pass123","role":"admin"}'

# Step 2: Login and get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Pass123"}'

# Step 3: Use token
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/auth/me
```
✅ **Expected:** Returns authenticated user info

---

### 2️⃣ RAG Pipeline (Core Component)
```bash
# List models
curl http://localhost:8000/benchmark/models

# List scenarios
curl http://localhost:8000/benchmark/scenarios
```
✅ **Expected:** Returns list of models and scenarios (may be empty if not seeded)

---

### 3️⃣ LLM Client (Core Component)
```bash
python -c "
from src.models_clients.ollama_client import check_ollama_health
is_available = check_ollama_health()
print('Ollama available:', is_available)
"
```
✅ **Expected:** Prints True if Ollama is running

---

### 4️⃣ Evaluation (Core Component)
```bash
python -c "
from src.utils.validation import validate_email, validate_password

# Test validation
assert validate_email('test@test.com')
is_valid, _ = validate_password('Pass123')
assert is_valid
print('✓ Validation functions working')
"
```
✅ **Expected:** Prints success message

---

### 5️⃣ Agent Pipeline (Core Component)
```bash
python -c "
from src.agents.graph import benchmark_graph
print('✓ Agent pipeline compiled')
"
```
✅ **Expected:** Prints success message

---

### 6️⃣ API & Pagination (Core Component)
```bash
# Query with pagination
curl "http://localhost:8000/benchmark/results?limit=10&offset=0"
```
✅ **Expected:** Returns paginated results

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: psycopg2` | `pip install psycopg2-binary` |
| Connection refused (database) | Start Docker: `docker run -p 5432:5432 -e POSTGRES_PASSWORD=... -d ankane/pgvector:latest` |
| Connection refused (Ollama) | Start Ollama: `ollama serve` |
| Port 8000 in use | Use different port: `uvicorn ... --port 8001` |
| Tests fail | `pip install --upgrade pytest pytest-mock` |

---

## 📁 Project Structure

```
.
├── src/
│   ├── api/                    # FastAPI endpoints
│   ├── agents/                 # LangGraph agents
│   ├── auth/                   # Authentication
│   ├── database/               # Database models & connection
│   ├── rag/                    # Vector store & retrieval
│   ├── models_clients/         # LLM clients (Ollama, etc.)
│   ├── evaluation/             # Ragas metrics evaluation
│   └── utils/                  # Utilities (validation, logging, etc.)
├── tests/                      # Unit tests (100+)
├── STARTUP_GUIDE.md            # ← Read this first!
├── DEPLOYMENT_STEPS.md         # ← Detailed setup
├── FIXES_SUMMARY.md            # ← What was fixed
└── .env.example                # ← Configuration template
```

---

## 🎯 Your Workflow

### First Time Setup (15 min)
1. Read: `STARTUP_GUIDE.md` (this guides setup)
2. Follow: Each step carefully
3. Verify: Each component works

### Development (ongoing)
1. Edit code in `src/`
2. Run tests: `pytest tests/ -v`
3. Test endpoint: Use Swagger UI at `/docs`
4. Check logs: `logs/benchmark.log`

### Deployment (when ready)
1. Update `.env` with production settings
2. Read: `DEPLOYMENT_STEPS.md`
3. Follow: Deployment checklist
4. Verify: All components working

---

## 🔑 Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start database (Docker)
docker run -p 5432:5432 -e POSTGRES_PASSWORD=ooredoo_pass -d ankane/pgvector:latest

# Initialize database
python -m src.database.init_db

# Run all tests
pytest tests/ -v

# Run specific component tests
pytest tests/test_utils.py -v           # Validation
pytest tests/test_auth_utils.py -v      # Authentication
pytest tests/test_vector_store.py -v    # Vector store

# Start API server
uvicorn src.api.main:app --reload

# Check Ollama
curl http://localhost:11434/api/tags
```

---

## 📖 Reading Guide

**Pick one based on your situation:**

| Situation | Read |
|-----------|------|
| "I just cloned the repo" | STARTUP_GUIDE.md |
| "Setup is failing" | STARTUP_GUIDE.md → Troubleshooting |
| "Want technical details" | FIXES_SUMMARY.md |
| "Want implementation examples" | IMPLEMENTATION_GUIDE.md |
| "Need to deploy to production" | DEPLOYMENT_STEPS.md |
| "Want to verify everything" | VERIFICATION_CHECKLIST.md |

---

## ✨ What's Included

This project includes:

✅ **Secure API** with authentication & authorization  
✅ **RAG Pipeline** with vector store & semantic search  
✅ **LLM Integration** with retry logic & error handling  
✅ **Evaluation Framework** with Ragas metrics  
✅ **100+ Unit Tests** with proper mocking  
✅ **Structured Logging** throughout  
✅ **Query Pagination** for scalability  
✅ **Complete Documentation** for setup & usage  

---

## 🎓 Learning Resources

- **FastAPI Docs**: http://localhost:8000/docs (when running)
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **LangChain**: https://python.langchain.com/
- **PostgreSQL/pgvector**: https://github.com/pgvector/pgvector

---

## ❓ FAQ

**Q: Do I need Docker?**  
A: No, but it's recommended for PostgreSQL. You can use existing PostgreSQL.

**Q: Do I need Ollama?**  
A: No, but many tests work better with it. Optional for development.

**Q: Can I use SQLite?**  
A: Yes, for testing only. Change `DATABASE_URL=sqlite:///test.db` in .env

**Q: How do I reset the database?**  
A: `docker exec postgres-ooredoo psql -U ooredoo_user -c "DROP DATABASE ai_benchmark;" ` then reinitialize.

**Q: Where are the logs?**  
A: Console output and `logs/benchmark.log`

**Q: How do I add API keys?**  
A: Add them to `.env`: `OPENAI_API_KEY=sk-...`

---

## 🚀 Next Steps

1. **NOW**: Read `STARTUP_GUIDE.md` and follow the steps
2. **THEN**: Get your first component working (Auth)
3. **NEXT**: Test each component systematically
4. **AFTER**: Read component-specific documentation
5. **FINALLY**: Deploy to your environment

---

## 📞 Support

- **Setup Issues**: See `STARTUP_GUIDE.md` → Troubleshooting
- **Code Questions**: Check docstrings in source files
- **API Help**: Visit http://localhost:8000/docs
- **Test Help**: Run `pytest tests/ -v -s` for details

---

**Ready? Let's go! Open `STARTUP_GUIDE.md` and follow the steps.** 🚀

---

**Last Updated:** August 2026  
**Project Status:** ✅ Production Ready  
**Documentation:** Complete
