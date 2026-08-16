"""
Point d'entrée FastAPI du projet Benchmark Ooredoo.

Lancer avec :
    uvicorn src.api.main:app --reload --port 8000

Documentation auto générée sur :
    http://localhost:8000/docs
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import benchmark, results, auth
from src.api.auth import get_current_user
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Benchmark des Outils IA Adapté aux Besoins Métiers",
    description="API REST pour piloter le pipeline LangGraph de benchmark multi-LLM (stage Ooredoo Tunisie).",
    version="1.0.0",
)

# CORS configuration - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Include routers
app.include_router(auth.router)
app.include_router(benchmark.router)
app.include_router(results.router)


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint - no authentication required."""
    return {
        "status": "ok",
        "message": "API Benchmark Ooredoo opérationnelle",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
def detailed_health_check(user: dict = Depends(get_current_user)):
    """Detailed health check - requires authentication."""
    return {
        "status": "ok",
        "authenticated_user": user["email"],
        "role": user["role"],
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }


# Log startup
@app.on_event("startup")
async def startup_event():
    logger.info("Benchmark API starting up...")
    logger.info(f"Environment: {__import__('os').getenv('ENVIRONMENT', 'development')}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Benchmark API shutting down...")