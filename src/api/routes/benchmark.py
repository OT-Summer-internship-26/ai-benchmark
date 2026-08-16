"""
Routes de pilotage du benchmark.

POST /benchmark/run       -> lance benchmark_graph.invoke(config) [requires admin/super_admin]
GET  /benchmark/models    -> liste les modèles disponibles (table modeles) [public]
GET  /benchmark/scenarios -> liste les scénarios disponibles (table scenarios) [public]
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from src.database.connection import engine
from src.api.models import BenchmarkRunRequest
from src.api.auth import get_current_user, require_any_role
from src.utils.logger import setup_logger
from src.utils.validation import validate_list_not_empty
from src.utils.exceptions import ValidationException

# Import du graphe LangGraph déjà compilé (Sprint 3)
from src.agents.graph import benchmark_graph

logger = setup_logger(__name__)
router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.post("/run")
def run_benchmark(
    request: BenchmarkRunRequest,
    user: dict = Depends(require_any_role("admin", "super_admin"))
):
    """
    Lance le pipeline complet : collecteur -> executeur -> evaluateur -> consolidateur.
    
    Requires: admin or super_admin role
    Valide les scenario_ids et model_names avant de passer au graphe.
    """
    try:
        logger.info(f"Benchmark run initiated by {user['email']}")
        
        # Validate input
        is_valid, error_msg = validate_list_not_empty(request.scenario_ids)
        if not is_valid:
            logger.error(f"Invalid benchmark request: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        is_valid, error_msg = validate_list_not_empty(request.model_names)
        if not is_valid:
            logger.error(f"Invalid benchmark request: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        scenario_ids = request.scenario_ids
        model_names = request.model_names
        
        logger.info(f"Benchmark: {len(scenario_ids)} scenarios, {len(model_names)} models by {user['email']}")
        
        # Verify scenarios exist
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM scenarios WHERE id = ANY(:ids)"),
                {"ids": scenario_ids}
            )
            existing_count = result.scalar()
            
            if existing_count == 0:
                msg = "None of the provided scenario IDs exist"
                logger.error(msg)
                raise HTTPException(status_code=404, detail=msg)
            
            if existing_count < len(scenario_ids):
                logger.warning(f"Only {existing_count}/{len(scenario_ids)} scenarios found")

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
            logger.error(f"Benchmark execution failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erreur pendant le benchmark : {str(e)}")

        executions = resultat.get("executions", [])
        scenarios = resultat.get("scenarios", [])
        erreurs = resultat.get("erreurs", [])

        logger.info(f"Benchmark completed: {len(executions)} executions, {len(erreurs)} errors")

        return {
            "status": "completed" if not erreurs else "completed_with_errors",
            "nb_scenarios": len(scenarios),
            "nb_models": len(model_names),
            "nb_executions": len(executions),
            "rapport": resultat.get("rapport"),
            "erreurs": erreurs,
            "initiated_by": user["email"],
        }
        
    except HTTPException:
        raise
    except ValidationException as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in benchmark: {str(e)}")
        raise HTTPException(status_code=500, detail="Une erreur interne s'est produite")


@router.get("/models")
def list_models(limit: int = Query(100, ge=1, le=1000)):
    """
    Retourne la liste des modèles enregistrés en base (table modeles).
    Public endpoint - no authentication required.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, nom, fournisseur, version, cout_par_1k_tokens, date_ajout "
                    "FROM modeles ORDER BY id LIMIT :limit"
                ),
                {"limit": limit}
            )
            rows = [dict(row) for row in result.mappings()]
            logger.debug(f"Retrieved {len(rows)} models from database")
            return {"count": len(rows), "modeles": rows}
    except Exception as e:
        logger.error(f"Error retrieving models: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")


@router.get("/scenarios")
def list_scenarios(limit: int = Query(100, ge=1, le=1000)):
    """
    Retourne la liste des scénarios enregistrés en base (table scenarios).
    Public endpoint - no authentication required.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, departement, metier, nom_cas_usage "
                    "FROM scenarios ORDER BY id LIMIT :limit"
                ),
                {"limit": limit}
            )
            rows = [dict(row) for row in result.mappings()]
            logger.debug(f"Retrieved {len(rows)} scenarios from database")
            return {"count": len(rows), "scenarios": rows}
    except Exception as e:
        logger.error(f"Error retrieving scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scenarios")
