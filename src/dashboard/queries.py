"""
Data layer for dashboard queries.

This module provides:
1. get_scenario_catalog() - The authoritative scenario catalogue, independent of scores
2. load_executions_by_department() - Load filtered executions for a specific department
3. load_executions_for_departments() - Load executions for multiple departments
4. get_client_recommendation() - A department-gated client recommendation
5. Helper functions for score aggregation and filtering
"""

import pandas as pd
from sqlalchemy import text, bindparam
from src.database.connection import engine


RAGAS_CRITERIA = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


def get_scenario_catalog() -> pd.DataFrame:
    """Return every configured scenario directly from ``scenarios``.

    This is deliberately independent of ``executions`` and ``scores``.  It is
    the sole source for dashboard scenario filters and coverage views, so a
    scenario cannot disappear merely because it has not been benchmarked yet.
    """
    with engine.connect() as conn:
        return pd.read_sql(
            text(
                """
                SELECT id AS scenario_id, departement, nom_cas_usage
                FROM scenarios
                ORDER BY departement, nom_cas_usage
                """
            ),
            conn,
        )


def get_client_department(client_email: str) -> str | None:
    """Return the department assigned to this client account, if any.

    The role predicate is intentional: an admin email can never be used to
    obtain a client-scoped result through this data layer.
    """
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT departement
                FROM utilisateurs
                WHERE email = :client_email
                  AND role = 'client'
                  AND departement IS NOT NULL
                """
            ),
            {"client_email": client_email},
        ).scalar()


def get_client_recommendation(
    client_email: str,
    min_scored_executions: int = 2,
) -> dict:
    """Return one plain recommendation for the authenticated client's scope.

    The department is never supplied by the caller.  Every query derives it
    from ``utilisateurs`` for ``client_email`` and joins that one-row scope to
    ``scenarios``.  This keeps the department restriction in SQL instead of
    relying on a UI selection.
    """
    department = get_client_department(client_email)
    if not department:
        return {"status": "no_department", "department": None, "recommendation": None}

    with engine.connect() as conn:
        execution_count = conn.execute(
            text(
                """
                WITH client_scope AS (
                    SELECT departement
                    FROM utilisateurs
                    WHERE email = :client_email
                      AND role = 'client'
                      AND departement IS NOT NULL
                )
                SELECT COUNT(e.id)
                FROM client_scope cs
                JOIN scenarios s ON s.departement = cs.departement
                LEFT JOIN executions e ON e.scenario_id = s.id
                """
            ),
            {"client_email": client_email},
        ).scalar() or 0

        if execution_count == 0:
            return {
                "status": "no_data",
                "department": department,
                "recommendation": None,
            }

        ranking = pd.read_sql(
            text(
                """
                WITH client_scope AS (
                    SELECT departement
                    FROM utilisateurs
                    WHERE email = :client_email
                      AND role = 'client'
                      AND departement IS NOT NULL
                ),
                valid_executions AS (
                    SELECT
                        e.id AS execution_id,
                        e.modele_id,
                        AVG(sc.note) AS quality_score,
                        AVG(e.latence_secondes) AS avg_latency
                    FROM client_scope cs
                    JOIN scenarios s ON s.departement = cs.departement
                    JOIN executions e ON e.scenario_id = s.id
                    JOIN scores sc ON sc.execution_id = e.id
                    WHERE sc.critere IN (
                        'faithfulness', 'answer_relevancy',
                        'context_precision', 'context_recall'
                    )
                      
                      AND sc.note BETWEEN 0 AND 1
                    GROUP BY e.id, e.modele_id
                    HAVING COUNT(DISTINCT sc.critere) = 4
                ),
                ranked_models AS (
                    SELECT
                        m.nom AS model_name,
                        AVG(ve.quality_score) AS quality_score,
                        AVG(ve.avg_latency) AS avg_latency,
                        COUNT(*) AS scored_executions
                    FROM valid_executions ve
                    JOIN modeles m ON m.id = ve.modele_id
                    GROUP BY m.id, m.nom
                    HAVING COUNT(*) >= :min_scored_executions
                )
                SELECT
                    model_name,
                    quality_score,
                    avg_latency,
                    scored_executions,
                    AVG(avg_latency) OVER () AS peer_avg_latency
                FROM ranked_models
                ORDER BY quality_score DESC, scored_executions DESC, avg_latency ASC
                LIMIT 1
                """
            ),
            conn,
            params={
                "client_email": client_email,
                "min_scored_executions": min_scored_executions,
            },
        )

    if ranking.empty:
        return {
            "status": "insufficient_data",
            "department": department,
            "recommendation": None,
        }

    best = ranking.iloc[0]
    return {
        "status": "ready",
        "department": department,
        "recommendation": {
            "model_name": best["model_name"],
            # These values remain server-side inputs for the wording below;
            # the client page intentionally never displays raw scores.
            "is_faster_than_peers": bool(best["avg_latency"] <= best["peer_avg_latency"]),
        },
    }


def load_executions_by_department(
    department: str,
    limit: int | None = 300,
    ragas_only: bool = True,
) -> pd.DataFrame:
    """
    Load all executions for a specific department (client-facing query).
    
    This is the PRIMARY query used by the client role. It ensures strict
    data isolation: client sees ONLY their department's results.
    
    Args:
        department: Department name (exact match)
        limit: Max number of executions to load (None = all)
        ragas_only: If True, exclude legacy heuristic scores from aggregation
        
    Returns:
        DataFrame with columns:
        - execution_id, scenario_id, nom_cas_usage, departement
        - modele_id, modele_nom
        - reponse_generee, latence_secondes, cout_estime, date_execution
        - score_global_display, faithfulness, answer_relevancy, context_precision, context_recall
        
    Note:
        Empty DataFrame if no executions found for this department.
    """
    limit_clause = "LIMIT :limit" if limit is not None else ""
    
    with engine.connect() as conn:
        # Main query: executions for this department's scenarios only
        executions = pd.read_sql(
            text(
                f"""
                SELECT
                    e.id AS execution_id,
                    e.scenario_id,
                    s.nom_cas_usage,
                    s.departement,
                    m.id AS modele_id,
                    m.nom AS modele_nom,
                    e.reponse_generee,
                    e.latence_secondes,
                    e.cout_estime,
                    e.date_execution
                FROM executions e
                JOIN scenarios s ON s.id = e.scenario_id
                JOIN modeles m ON m.id = e.modele_id
                WHERE s.departement = :department
                ORDER BY e.date_execution DESC
                {limit_clause}
                """
            ),
            conn,
            params={
                "department": department,
                "limit": limit
            } if limit is not None else {"department": department},
        )

        if executions.empty:
            return executions

        # Fetch scores, filtering by methode if ragas_only
        execution_ids = executions["execution_id"].tolist()
        
        where_clause = "AND methode = 'ragas'" if ragas_only else ""
        
        scores_query = text(
            f"""
            SELECT execution_id, critere, note, commentaire 
            FROM scores 
            WHERE execution_id IN :ids
            AND (
                critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                OR (critere='score_global' AND note <= 1.0)
            )
            {where_clause}
            """
        ).bindparams(bindparam("ids", expanding=True))

        scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})

    if scores.empty:
        executions["score_global_display"] = None
        executions["faithfulness"] = None
        executions["answer_relevancy"] = None
        executions["context_precision"] = None
        executions["context_recall"] = None
        return executions

    # Pivot scores
    pivot_scores = scores.pivot_table(
        index="execution_id",
        columns="critere",
        values="note",
        aggfunc="first",
    ).reset_index()

    df = executions.merge(pivot_scores, on="execution_id", how="left")
    
    # Compute global score as average of Ragas metrics
    ragas_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    df["score_global_display"] = (
        df[[c for c in ragas_cols if c in df.columns]]
        .mean(axis=1)
        .round(3)
    )
    
    return df


def load_executions_for_departments(
    departments: list[str],
    limit: int | None = 300,
    ragas_only: bool = True,
) -> pd.DataFrame:
    """
    Load executions for multiple departments (admin-facing query).
    
    Args:
        departments: List of department names
        limit: Max number of executions (None = all)
        ragas_only: If True, exclude legacy heuristic scores
        
    Returns:
        DataFrame with all executions from specified departments
        
    Note:
        Empty DataFrame if no executions found.
    """
    if not departments:
        return pd.DataFrame()
    
    limit_clause = "LIMIT :limit" if limit is not None else ""
    
    with engine.connect() as conn:
        query_text = f"""
                SELECT
                    e.id AS execution_id,
                    e.scenario_id,
                    s.nom_cas_usage,
                    s.departement,
                    m.id AS modele_id,
                    m.nom AS modele_nom,
                    e.reponse_generee,
                    e.latence_secondes,
                    e.cout_estime,
                    e.date_execution
                FROM executions e
                JOIN scenarios s ON s.id = e.scenario_id
                JOIN modeles m ON m.id = e.modele_id
                WHERE s.departement = ANY(:departments)
                ORDER BY e.date_execution DESC
                {limit_clause}
                """
        
        query_obj = text(query_text)
        
        params = {
            "departments": departments,
        }
        if limit is not None:
            params["limit"] = limit
            
        executions = pd.read_sql(query_obj, conn, params=params)

        if executions.empty:
            return executions

        execution_ids = executions["execution_id"].tolist()
        
        where_clause = "AND methode = 'ragas'" if ragas_only else ""
        
        scores_query = text(
            f"""
            SELECT execution_id, critere, note, commentaire 
            FROM scores 
            WHERE execution_id IN :ids
            AND (
                critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                OR (critere='score_global' AND note <= 1.0)
            )
            {where_clause}
            """
        ).bindparams(bindparam("ids", expanding=True))

        scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})

    if scores.empty:
        executions["score_global_display"] = None
        executions["faithfulness"] = None
        executions["answer_relevancy"] = None
        executions["context_precision"] = None
        executions["context_recall"] = None
        return executions

    pivot_scores = scores.pivot_table(
        index="execution_id",
        columns="critere",
        values="note",
        aggfunc="first",
    ).reset_index()

    df = executions.merge(pivot_scores, on="execution_id", how="left")
    
    ragas_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    df["score_global_display"] = (
        df[[c for c in ragas_cols if c in df.columns]]
        .mean(axis=1)
        .round(3)
    )
    
    return df


def get_best_model_for_department(
    department: str,
    min_executions: int = 2,
) -> dict | None:
    """
    Get the single best-ranked model for a specific department.
    
    Used by client recommendation page to show ONLY the top model for their dept.
    
    Args:
        department: Department name
        min_executions: Minimum number of executions before considering a model
        
    Returns:
        Dict with keys:
        {
            "model_name": str,
            "model_id": int,
            "avg_score": float,
            "avg_latency": float,
            "num_scenarios": int,
            "num_executions": int,
            "top_scenarios": list[str]  # Top 3 scenarios where this model performed best
        }
        
        None if no models meet criteria.
    """
    with engine.connect() as conn:
        # Get model rankings for this department
        query = text("""
            SELECT
                m.id,
                m.nom,
                AVG(CASE 
                    WHEN (f.note + ar.note + cp.note + cr.note) / 4.0 IS NOT NULL 
                    THEN (f.note + ar.note + cp.note + cr.note) / 4.0
                    ELSE NULL
                END) as avg_score,
                AVG(e.latence_secondes) as avg_latency,
                COUNT(DISTINCT s.id) as num_scenarios,
                COUNT(DISTINCT e.id) as num_executions
            FROM executions e
            JOIN modeles m ON m.id = e.modele_id
            JOIN scenarios s ON s.id = e.scenario_id
            LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.methode = 'ragas'
            LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.methode = 'ragas'
            LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.methode = 'ragas'
            LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.methode = 'ragas'
            WHERE s.departement = :department
            GROUP BY m.id, m.nom
            HAVING COUNT(DISTINCT e.id) >= :min_executions
            ORDER BY avg_score DESC, num_executions DESC
            LIMIT 1
        """)
        
        result = conn.execute(query, {"department": department, "min_executions": min_executions}).fetchone()
        
        if not result:
            return None
        
        model_id, model_name, avg_score, avg_latency, num_scenarios, num_executions = result
        
        # Get top 3 scenarios where this model performed best
        top_scenarios_query = text("""
            SELECT
                s.nom_cas_usage,
                AVG((f.note + ar.note + cp.note + cr.note) / 4.0) as scenario_score
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.methode = 'ragas'
            LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.methode = 'ragas'
            LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.methode = 'ragas'
            LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.methode = 'ragas'
            WHERE e.modele_id = :model_id
            AND s.departement = :department
            GROUP BY s.id, s.nom_cas_usage
            ORDER BY scenario_score DESC
            LIMIT 3
        """)
        
        top_scenarios = [
            row[0] for row in conn.execute(
                top_scenarios_query,
                {"model_id": model_id, "department": department}
            ).fetchall()
        ]
        
        return {
            "model_id": model_id,
            "model_name": model_name,
            "avg_score": round(avg_score or 0.0, 3),
            "avg_latency": round(avg_latency or 0.0, 2),
            "num_scenarios": num_scenarios,
            "num_executions": num_executions,
            "top_scenarios": top_scenarios,
        }


def get_department_summary_stats(department: str) -> dict:
    """
    Get summary statistics for a department (for display on recommendation page).
    
    Args:
        department: Department name
        
    Returns:
        Dict with:
        {
            "num_scenarios": int,
            "num_models_tested": int,
            "total_executions": int,
            "date_first_execution": str,
            "date_last_execution": str,
        }
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                COUNT(DISTINCT s.id) as num_scenarios,
                COUNT(DISTINCT m.id) as num_models_tested,
                COUNT(DISTINCT e.id) as total_executions,
                MIN(e.date_execution) as date_first_execution,
                MAX(e.date_execution) as date_last_execution
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            JOIN modeles m ON m.id = e.modele_id
            WHERE s.departement = :department
        """)
        
        result = conn.execute(query, {"department": department}).fetchone()
        
        if not result:
            return {
                "num_scenarios": 0,
                "num_models_tested": 0,
                "total_executions": 0,
                "date_first_execution": None,
                "date_last_execution": None,
            }
        
        return {
            "num_scenarios": result[0],
            "num_models_tested": result[1],
            "total_executions": result[2],
            "date_first_execution": str(result[3]) if result[3] else None,
            "date_last_execution": str(result[4]) if result[4] else None,
        }
