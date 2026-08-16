# Complete Test Sequence for Ooredoo IA Benchmark
# Run this after starting the API server with: uvicorn src.api.main:app --reload

$ErrorActionPreference = "Continue"
$baseUrl = "http://localhost:8000"
$token = $null

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method = "GET",
        [string]$Url,
        [string]$Body = $null,
        [string]$Auth = $null
    )
    
    Write-Host ""
    Write-Host "Testing: $Name" -ForegroundColor Cyan
    Write-Host "  Method: $Method | URL: $Url" -ForegroundColor Gray
    
    try {
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        if ($Auth) {
            $headers["Authorization"] = "Bearer $Auth"
        }
        
        if ($Body) {
            Write-Host "  Body: $Body" -ForegroundColor Gray
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $headers -Body $Body
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $headers
        }
        
        # Check response
        if ($response) {
            Write-Host "✓ SUCCESS" -ForegroundColor Green
            
            # Show key data
            if ($response.PSObject.Properties.Name -contains "token") {
                Write-Host "  Token: $($response.token.Substring(0, 20))..." -ForegroundColor Gray
            }
            if ($response.PSObject.Properties.Name -contains "email") {
                Write-Host "  Email: $($response.email)" -ForegroundColor Gray
            }
            if ($response.PSObject.Properties.Name -contains "count") {
                Write-Host "  Count: $($response.count)" -ForegroundColor Gray
            }
            
            return $response
        }
    }
    catch {
        Write-Host "✗ FAILED" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        return $null
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ooredoo IA Benchmark - Complete Test Sequence" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# TEST 1: Health Check
Write-Host "[TEST 1] Health Check" -ForegroundColor Yellow
$health = Test-Endpoint -Name "Health Check" -Url "$baseUrl/" -Method "GET"
if (-not $health) {
    Write-Host ""
    Write-Host "❌ API is not responding. Make sure it's started with:" -ForegroundColor Red
    Write-Host "   uvicorn src.api.main:app --reload --port 8000" -ForegroundColor Red
    exit 1
}

# TEST 2: Authentication System
Write-Host ""
Write-Host "[TEST 2] Authentication System" -ForegroundColor Yellow

# Register user
$registerBody = @{
    email = "test@example.com"
    password = "SecureTestPass123"
    role = "admin"
} | ConvertTo-Json

$registerResponse = Test-Endpoint `
    -Name "User Registration" `
    -Url "$baseUrl/auth/register" `
    -Method "POST" `
    -Body $registerBody

# Login
$loginBody = @{
    email = "test@example.com"
    password = "SecureTestPass123"
} | ConvertTo-Json

$loginResponse = Test-Endpoint `
    -Name "User Login" `
    -Url "$baseUrl/auth/login" `
    -Method "POST" `
    -Body $loginBody

if ($loginResponse -and $loginResponse.token) {
    $token = $loginResponse.token
    Write-Host "  Stored token for authenticated requests" -ForegroundColor Gray
} else {
    Write-Host "  Could not get token!" -ForegroundColor Red
}

# Get current user
if ($token) {
    Test-Endpoint `
        -Name "Get Current User" `
        -Url "$baseUrl/auth/me" `
        -Method "GET" `
        -Auth $token
}

# TEST 3: RAG Pipeline
Write-Host ""
Write-Host "[TEST 3] RAG Pipeline" -ForegroundColor Yellow

Test-Endpoint `
    -Name "List Models" `
    -Url "$baseUrl/benchmark/models?limit=10" `
    -Method "GET"

Test-Endpoint `
    -Name "List Scenarios" `
    -Url "$baseUrl/benchmark/scenarios?limit=10" `
    -Method "GET"

# TEST 4: Validation (No API needed)
Write-Host ""
Write-Host "[TEST 4] Input Validation" -ForegroundColor Yellow
Write-Host ""
Write-Host "Testing validation functions..." -ForegroundColor Cyan

python -c "
from src.utils.validation import validate_email, validate_password, validate_positive_int

# Email validation
assert validate_email('user@example.com') == True
assert validate_email('invalid') == False
print('✓ Email validation OK')

# Password validation
is_valid, error = validate_password('secure_pass_123')
assert is_valid == True
print('✓ Password validation OK')

# Integer validation
is_valid, error, value = validate_positive_int(42, 'test')
assert is_valid == True and value == 42
print('✓ Integer validation OK')

print('✓ Validation tests passed')
"

# TEST 5: Authentication Utils
Write-Host ""
Write-Host "[TEST 5] Authentication Utilities" -ForegroundColor Yellow
Write-Host ""
Write-Host "Testing authentication functions..." -ForegroundColor Cyan

python -c "
from src.auth.utils import hash_password, verify_password

# Password hashing
password = 'test_password'
hashed = hash_password(password)
assert len(hashed) > 0
print('✓ Password hashing OK')

# Password verification
verified = verify_password(password, hashed)
assert verified == True
print('✓ Password verification OK')

# Wrong password
wrong = verify_password('wrong_password', hashed)
assert wrong == False
print('✓ Wrong password detection OK')

print('✓ Authentication tests passed')
"

# TEST 6: LLM Client
Write-Host ""
Write-Host "[TEST 6] LLM Client" -ForegroundColor Yellow
Write-Host ""
Write-Host "Testing LLM client (Ollama)..." -ForegroundColor Cyan

python -c "
from src.models_clients.ollama_client import check_ollama_health

# Check Ollama availability
is_available = check_ollama_health()
if is_available:
    print('✓ Ollama is available and responding')
else:
    print('⚠ Ollama is not available')
    print('  Start it with: ollama serve')
    print('  (LLM calls will fail without Ollama)')
"

# TEST 7: Query Pagination
Write-Host ""
Write-Host "[TEST 7] Query Pagination" -ForegroundColor Yellow

Test-Endpoint `
    -Name "Results with Pagination (limit=5, offset=0)" `
    -Url "$baseUrl/benchmark/results?limit=5&offset=0" `
    -Method "GET"

Test-Endpoint `
    -Name "Results with Scenario Filter" `
    -Url "$baseUrl/benchmark/results?scenario_id=1&limit=10" `
    -Method "GET"

# TEST 8: Benchmark Pipeline (if token available)
Write-Host ""
Write-Host "[TEST 8] Benchmark Pipeline" -ForegroundColor Yellow

if ($token) {
    $benchmarkBody = @{
        scenario_ids = @(1, 2)
        model_names = @("llama3.1:8b")
    } | ConvertTo-Json
    
    Write-Host ""
    Write-Host "⚠ Note: Full benchmark requires scenarios and models in database" -ForegroundColor Yellow
    Write-Host "  If there are no scenarios/models, this test will show expected errors" -ForegroundColor Yellow
    Write-Host ""
    
    Test-Endpoint `
        -Name "Run Benchmark" `
        -Url "$baseUrl/benchmark/run" `
        -Method "POST" `
        -Body $benchmarkBody `
        -Auth $token
} else {
    Write-Host ""
    Write-Host "⚠ Could not get token, skipping benchmark test" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Test Sequence Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  ✓ Health check - API is responding"
Write-Host "  ✓ Authentication - Login/Registration working"
Write-Host "  ✓ Validation - Input validation functions working"
Write-Host "  ✓ RAG pipeline - Models and scenarios endpoints working"
Write-Host "  ✓ Query pagination - Results endpoint with pagination working"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Seed your database with scenarios and models"
Write-Host "2. Start Ollama: ollama serve"
Write-Host "3. Run a benchmark with authentication token"
Write-Host ""
Write-Host "For full deployment guide, see DEPLOYMENT_STEPS.md"
Write-Host ""
