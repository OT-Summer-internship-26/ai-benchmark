"""
Routes de pilotage du benchmark.

POST /benchmark/run       -> lance benchmark_graph.invoke(config)
GET  /benchmark/models    -> liste les modèles disponibles (table modeles)
GET  /benchmark/scenarios -> liste les scénarios disponibles (table scenarios)
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from src.api.db import engine
from src.api.schemas import BenchmarkRunRequest, BenchmarkRunResponse

# Import du graphe LangGraph déjà compilé (Sprint 3)
from src.agents.graph import benchmark_graph

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/run", response_model=BenchmarkRunResponse)
def run_benchmark(request: BenchmarkRunRequest):
    """
    Lance le pipeline complet : collecteur -> executeur -> evaluateur -> consolidateur.

    agent_collecteur fait state["scenario_ids"] directement (pas de valeur par défaut),
    donc on résout toujours une vraie liste d'IDs ici, avant d'appeler le graphe.
    """
    scenario_ids = request.scenario_ids
    model_names = request.model_names

    with engine.connect() as conn:
        if not scenario_ids:
            result = conn.execute(text("SELECT id FROM scenarios ORDER BY id"))
            scenario_ids = [row[0] for row in result]

        if not model_names:
            # Les 4 tags Ollama réels, alignés sur le mapping de src/agents/executeur.py
            # ({"llama3.1:8b": 9, "mistral:7b": 10, "gemma2:9b": 11, "qwen2.5:7b": 12}).
            # La colonne "nom" en base (ex: "Llama 3.1 8B (Ollama)") n'est PAS ce format,
            # donc on ne la lit pas ici — on utilise directement les tags attendus par l'exécuteur.
            model_names = ["llama3.1:8b", "mistral:7b", "gemma2:9b", "qwen2.5:7b"]

    config_initial = {
        "scenario_ids": scenario_ids,
        "model_names": model_names,
        "scenarios": [],
        "executions": [],
        "scores": [],
        "rapport": None,
        "erreurs": [],
    }

    try:
        resultat = benchmark_graph.invoke(config_initial)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur pendant le benchmark : {e}")

    executions = resultat.get("executions", [])
    scenarios = resultat.get("scenarios", [])
    erreurs = resultat.get("erreurs", [])

    return BenchmarkRunResponse(
        status="termine" if not erreurs else "termine_avec_erreurs",
        nb_scenarios=len(scenarios),
        nb_modeles=len(model_names),
        nb_executions=len(executions),
        rapport=resultat.get("rapport"),
        erreurs=erreurs,
    )


@router.get("/models")
def list_models():
    """Retourne la liste des modèles enregistrés en base (table modeles)."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, nom, fournisseur, version, cout_par_1k_tokens, date_ajout "
                "FROM modeles ORDER BY id"
            )
        )
        rows = [dict(row) for row in result.mappings()]
    return {"count": len(rows), "modeles": rows}


@router.get("/scenarios")
def list_scenarios():
    """Retourne la liste des scénarios enregistrés en base (table scenarios)."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, departement, metier, nom_cas_usage, type_categorie "
                "FROM scenarios ORDER BY id"
            )
        )
        rows = [dict(row) for row in result.mappings()]
    return {"count": len(rows), "scenarios": rows}