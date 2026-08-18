"""
Route GET /benchmark/results
Retourne les dernières exécutions avec leurs scores associés depuis executions + scores.
Avec pagination, filtrage, validation et QUERY-LEVEL GATING pour les clients.

SECURITY: Clients can ONLY query their assigned department.
This is enforced at the query level (SQL WHERE clause), not UI-level filtering.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy import text, bindparam
from src.database.connection import engine
from src.api.auth import get_current_user
from src.utils.logger import setup_logger
from src.utils.validation import validate_positive_int

logger = setup_logger(__name__)
router = APIRouter(prefix="/benchmark", tags=["results"])


@router.get("/results")
def get_results(
    limit: int = Query(default=50, ge=1, le=500, description="Nombre de résultats à retourner (pagination)"),
    offset: int = Query(default=0, ge=0, description="Décalage pour la pagination"),
    scenario_id: int | None = Query(default=None, ge=1, description="Filtrer par scénario"),
    modele_id: int | None = Query(default=None, ge=1, description="Filtrer par modèle"),
    user: dict = Depends(get_current_user),
):
    """
    Retourne les exécutions avec leurs scores associés (RAGAS et legacy).
    Inclut pagination avec limit/offset pour éviter les surcharges mémoire.
    
    SECURITY: Clients can ONLY access their assigned department.
    Query is enforced at database level (WHERE clause), not client-side filtering.
    
    Retourne:
        {
            "total_count": int,      # total avant pagination
            "returned_count": int,   # nombre retourné
            "limit": int,
            "offset": int,
            "results": [...]
        }
    """
    try:
        # === QUERY-LEVEL GATING FOR CLIENT ROLE ===
        # If user is a client, enforce department isolation at query level
        department_filter = None
        if user.get("role") == "client":
            # Get client's assigned department
            with engine.connect() as check_conn:
                dept_query = text("""
                    SELECT departement FROM utilisateurs WHERE id = :user_id
                """)
                dept_result = check_conn.execute(dept_query, {"user_id": user.get("id")}).fetchone()
                
                if not dept_result or not dept_result[0]:
                    logger.error(f"Client {user.get('email')} has no department assigned")
                    raise HTTPException(
                        status_code=403,
                        detail="Your account is not assigned to a department. Contact admin."
                    )
                
                department_filter = dept_result[0]
                logger.info(f"Client {user.get('email')} querying department: {department_filter}")
        
        # Validate pagination parameters
        is_valid, error, limit = validate_positive_int(limit, "limit")
        if not is_valid:
            logger.warning(f"Invalid limit parameter: {error}")
            raise HTTPException(status_code=400, detail=error)
        
        # Validate offset (must be >= 0, not > 0)
        if not isinstance(offset, int) or offset < 0:
            logger.warning(f"Invalid offset parameter: offset must be non-negative")
            raise HTTPException(status_code=400, detail="offset must be non-negative")
        
        # Cap limit to prevent abuse
        limit = min(limit, 500)
        
        filtres = []
        params: dict = {"limit": limit, "offset": offset}

        # === ADD DEPARTMENT FILTER FOR CLIENTS ===
        if department_filter:
            filtres.append("s.departement = :department")
            params["department"] = department_filter

        if scenario_id is not None:
            if scenario_id <= 0:
                raise HTTPException(status_code=400, detail="scenario_id must be positive")
            filtres.append("e.scenario_id = :scenario_id")
            params["scenario_id"] = scenario_id
            
        if modele_id is not None:
            if modele_id <= 0:
                raise HTTPException(status_code=400, detail="modele_id must be positive")
            filtres.append("e.modele_id = :modele_id")
            params["modele_id"] = modele_id

        where_clause = f"WHERE {' AND '.join(filtres)}" if filtres else ""

        # Query to get total count (with filters applied, INCLUDING department filter)
        count_query = text(f"""
            SELECT COUNT(*) FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            {where_clause}
        """)

        # Main query with pagination
        query_executions = text(f"""
            SELECT
                e.id AS execution_id,
                e.scenario_id,
                s.nom_cas_usage,
                s.departement,
                e.modele_id,
                m.nom AS modele_nom,
                e.reponse_generee,
                e.latence_secondes,
                e.cout_estime,
                e.date_execution
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            JOIN modeles m ON m.id = e.modele_id
            {where_clause}
            ORDER BY e.date_execution DESC
            LIMIT :limit
            OFFSET :offset
        """)

        # RAGAS criteria (0.0-1.0 scale)
        raga_criteria = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
        legacy_criteria = ("completude", "structure", "fidelite_rag", "honnetete")

        with engine.connect() as conn:
            try:
                # Get total count
                total_count_result = conn.execute(count_query, params)
                total_count = total_count_result.scalar() or 0
                
                # Get paginated results
                executions = [dict(row) for row in conn.execute(query_executions, params).mappings()]

                if not executions:
                    logger.debug(f"No results found with filters: {filtres}")
                    return {
                        "total_count": total_count,
                        "returned_count": 0,
                        "limit": limit,
                        "offset": offset,
                        "results": []
                    }

                execution_ids = [row["execution_id"] for row in executions]

                # Fetch RAGAS scores
                query_scores = text(
                    "SELECT execution_id, critere, note, commentaire "
                    "FROM scores WHERE execution_id IN :ids AND critere IN :criteria"
                ).bindparams(bindparam("ids", expanding=True), bindparam("criteria", expanding=True))

                scores_rows = [
                    dict(row)
                    for row in conn.execute(query_scores, {"ids": execution_ids, "criteria": raga_criteria}).mappings()
                ]

                # Fetch legacy score markers
                query_legacy = text(
                    "SELECT execution_id, critere, note "
                    "FROM scores WHERE execution_id IN :ids AND (critere IN :legacy OR (critere='score_global' AND note > 1.0))"
                ).bindparams(bindparam("ids", expanding=True), bindparam("legacy", expanding=True))

                legacy_rows = [
                    dict(row)
                    for row in conn.execute(query_legacy, {"ids": execution_ids, "legacy": legacy_criteria}).mappings()
                ]
            except Exception as e:
                logger.error(f"Database query error: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to retrieve results")

        # Group scores by execution
        scores_par_execution: dict[int, list] = {}
        for row in scores_rows:
            scores_par_execution.setdefault(row["execution_id"], []).append(
                {
                    "critere": row["critere"],
                    "note": row["note"],
                    "commentaire": row["commentaire"],
                }
            )

        # Enrich execution results
        results = []
        for exe in executions:
            exe["scores"] = scores_par_execution.get(exe["execution_id"], [])
            
            # Check for legacy scores
            exe_legacy = [r for r in legacy_rows if r["execution_id"] == exe["execution_id"]]
            exe["has_legacy_scores"] = bool(exe_legacy)

            # Compute global score
            if exe["scores"]:
                notes = [s["note"] for s in exe["scores"] if s["note"] is not None]
                exe["score_global"] = round(sum(notes) / len(notes), 3) if notes else None
            else:
                exe["score_global"] = None
            
            results.append(exe)

        logger.debug(f"Retrieved {len(results)} results (total: {total_count})")

        return {
            "total_count": total_count,
            "returned_count": len(results),
            "limit": limit,
            "offset": offset,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_results: {str(e)}")
        raise HTTPException(status_code=500, detail="Une erreur interne s'est produite")