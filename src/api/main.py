"""
Point d'entrée FastAPI du projet Benchmark Ooredoo.

Lancer avec :
    uvicorn src.api.main:app --reload --port 8000

Documentation auto générée sur :
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import benchmark, results

app = FastAPI(
    title="Benchmark des Outils IA Adapté aux Besoins Métiers",
    description="API REST pour piloter le pipeline LangGraph de benchmark multi-LLM (stage Ooredoo Tunisie).",
    version="1.0.0",
)

# CORS ouvert pour permettre au dashboard Streamlit (Sprint 5) d'appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(benchmark.router)
app.include_router(results.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "API Benchmark Ooredoo opérationnelle"}