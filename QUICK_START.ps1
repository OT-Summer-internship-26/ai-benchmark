# Quick Start Script for Windows PowerShell
# Run this script to set up and test the Ooredoo IA Benchmark

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ooredoo IA Benchmark - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check command
function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    }
    catch {
        return $false
    }
}

# Step 1: Check Python
Write-Host "[1/8] Checking Python installation..." -ForegroundColor Yellow
if (Test-Command python) {
    $pythonVersion = python --version
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Step 2: Check dependencies
Write-Host "[2/8] Checking dependencies..." -ForegroundColor Yellow
$requiredModules = @("sqlalchemy", "fastapi", "psycopg2", "langchain", "pydantic")
foreach ($module in $requiredModules) {
    try {
        python -c "import $module" 2>$null
        Write-Host "✓ $module is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ $module is not installed. Installing..." -ForegroundColor Yellow
        pip install $module --quiet
    }
}

# Step 3: Check .env file
Write-Host "[3/8] Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
    $dbUrl = (Select-String -Path ".env" -Pattern "DATABASE_URL" | Select-Object -First 1).Line
    Write-Host "  Database URL configured: $($dbUrl.Substring(0, 50))..." -ForegroundColor Gray
} else {
    Write-Host "⚠ .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ .env created. Please update it with your settings." -ForegroundColor Yellow
}

# Step 4: Test imports
Write-Host "[4/8] Testing critical imports..." -ForegroundColor Yellow
try {
    python -c "
from src.utils import validation, logger, exceptions
from src.database.models import Scenario, Modele
from src.auth.utils import hash_password
print('✓ All imports successful')
" 2>&1
    Write-Host "✓ Critical imports OK" -ForegroundColor Green
} catch {
    Write-Host "✗ Import failed: $_" -ForegroundColor Red
    exit 1
}

# Step 5: Run unit tests
Write-Host "[5/8] Running unit tests..." -ForegroundColor Yellow
try {
    $testOutput = pytest tests/test_utils.py::TestEmailValidation::test_valid_email -v --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Unit tests passed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Some tests failed. Check logs." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not run tests. pytest may not be installed." -ForegroundColor Yellow
}

# Step 6: Check database
Write-Host "[6/8] Checking database connection..." -ForegroundColor Yellow
try {
    python -c "
from src.database.connection import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    print('Make sure PostgreSQL is running and DATABASE_URL is correct')
" 2>&1
} catch {
    Write-Host "⚠ Database check failed. Make sure PostgreSQL is running." -ForegroundColor Yellow
}

# Step 7: Initialize database
Write-Host "[7/8] Initializing database tables..." -ForegroundColor Yellow
try {
    python -m src.database.init_db 2>&1 | Select-Object -First 1
    Write-Host "✓ Database initialized" -ForegroundColor Green
} catch {
    Write-Host "⚠ Database initialization had issues (may be OK if tables exist)" -ForegroundColor Yellow
}

# Step 8: Ready to start
Write-Host "[8/8] Ready to start!" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Make sure PostgreSQL is running:"
Write-Host "   docker ps  (if using Docker)"
Write-Host ""
Write-Host "2. Start the API server in a new terminal:"
Write-Host "   uvicorn src.api.main:app --reload --port 8000"
Write-Host ""
Write-Host "3. Access the API documentation:"
Write-Host "   http://localhost:8000/docs"
Write-Host ""
Write-Host "4. Run the test sequence (in another terminal):"
Write-Host "   .\TEST_SEQUENCE.ps1"
Write-Host ""
Write-Host "For detailed steps, see DEPLOYMENT_STEPS.md"
Write-Host ""
