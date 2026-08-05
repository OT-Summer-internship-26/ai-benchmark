"""
Route GET /benchmark/results
Retourne les dernières exécutions avec leurs scores associés depuis executions + scores.
"""

from fastapi import APIRouter, Query
from sqlalchemy import text, bindparam

from src.api.db import engine

router = APIRouter(prefix="/benchmark", tags=["results"])


@router.get("/results")
def get_results(
    limit: int = Query(default=20, ge=1, le=200, description="Nombre d'exécutions à retourner"),
    scenario_id: int | None = Query(default=None, description="Filtrer par scénario"),
    modele_id: int | None = Query(default=None, description="Filtrer par modèle"),
):
    """
    Retourne les N dernières exécutions (les plus récentes en premier),
    chacune enrichie avec ses scores (une ligne par critère) et le nom du modèle/scénario.
    """
    filtres = []
    params: dict = {"limit": limit}

    if scenario_id is not None:
        filtres.append("e.scenario_id = :scenario_id")
        params["scenario_id"] = scenario_id
    if modele_id is not None:
        filtres.append("e.modele_id = :modele_id")
        params["modele_id"] = modele_id

    where_clause = f"WHERE {' AND '.join(filtres)}" if filtres else ""

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
    """)

    with engine.connect() as conn:
        executions = [dict(row) for row in conn.execute(query_executions, params).mappings()]

        if not executions:
            return {"count": 0, "results": []}

        execution_ids = [row["execution_id"] for row in executions]
        query_scores = text(
            "SELECT execution_id, critere, note, commentaire "
            "FROM scores WHERE execution_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))

        scores_rows = [
            dict(row) for row in conn.execute(query_scores, {"ids": execution_ids}).mappings()
        ]

    # Regrouper les scores par execution_id
    scores_par_execution: dict[int, list] = {}
    for row in scores_rows:
        scores_par_execution.setdefault(row["execution_id"], []).append(
            {
                "critere": row["critere"],
                "note": row["note"],
                "commentaire": row["commentaire"],
            }
        )

    results = []
    for exe in executions:
        exe["scores"] = scores_par_execution.get(exe["execution_id"], [])
        if exe["scores"]:
            notes = [s["note"] for s in exe["scores"] if s["note"] is not None]
            exe["score_global"] = round(sum(notes) / len(notes), 2) if notes else None
        else:
            exe["score_global"] = None
        results.append(exe)

    return {"count": len(results), "results": results}