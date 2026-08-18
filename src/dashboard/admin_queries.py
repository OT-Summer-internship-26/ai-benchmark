"""
Admin queries with cascading filters

Provides:
1. get_all_departments() - List all departments with execution counts
2. get_scenarios_for_departments() - Scenarios filtered by selected departments
3. get_models_for_departments() - Models tested in selected departments
4. get_department_model_comparison() - Multi-metric comparison across models in a department
5. get_department_leaderboard() - Ranked models by department
"""

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine


def get_all_departments() -> list[dict]:
    """
    Get all departments with execution and scenario counts.
    
    Used for admin department filter dropdown.
    
    Returns:
        List of dicts: {
            "name": str,
            "scenario_count": int,
            "execution_count": int,
            "models_tested": int
        }
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                s.departement,
                COUNT(DISTINCT s.id) as scenario_count,
                COUNT(DISTINCT e.id) as execution_count,
                COUNT(DISTINCT e.modele_id) as models_tested
            FROM scenarios s
            LEFT JOIN executions e ON e.scenario_id = s.id
            GROUP BY s.departement
            ORDER BY execution_count DESC, s.departement
        """)
        
        results = conn.execute(query).fetchall()
        
        return [
            {
                "name": row[0],
                "scenario_count": row[1],
                "execution_count": row[2] or 0,
                "models_tested": row[3] or 0,
            }
            for row in results
        ]


def get_scenarios_for_departments(departments: list[str]) -> list[dict]:
    """
    Get scenarios for selected departments (cascading filter).
    
    Args:
        departments: List of department names to filter by
        
    Returns:
        List of dicts: {
            "id": int,
            "nom_cas_usage": str,
            "departement": str,
            "execution_count": int,
            "scored_execution_count": int,
            "data_status": str
        }
    """
    if not departments:
        return []
    
    with engine.connect() as conn:
        query = text("""
            SELECT
                s.id,
                s.nom_cas_usage,
                s.departement,
                COUNT(DISTINCT e.id) as execution_count,
                COUNT(DISTINCT CASE WHEN (
                    SELECT COUNT(DISTINCT sc.critere)
                    FROM scores sc
                    WHERE sc.execution_id = e.id
                      AND sc.critere IN (
                          'faithfulness', 'answer_relevancy',
                          'context_precision', 'context_recall'
                      )
                      AND sc.methode = 'ragas'
                      AND COALESCE(sc.is_legacy, FALSE) = FALSE
                      AND sc.note BETWEEN 0 AND 1
                ) = 4 THEN e.id END) as scored_execution_count
            FROM scenarios s
            LEFT JOIN executions e ON e.scenario_id = s.id
            WHERE s.departement = ANY(:departments)
            GROUP BY s.id, s.nom_cas_usage, s.departement
            ORDER BY s.departement, s.nom_cas_usage
        """)
        
        results = conn.execute(query, {"departments": departments}).fetchall()
        
        return [
            {
                "id": row[0],
                "nom_cas_usage": row[1],
                "departement": row[2],
                "execution_count": row[3] or 0,
                "scored_execution_count": row[4] or 0,
                "data_status": (
                    "Données disponibles"
                    if (row[4] or 0) > 0
                    else "Aucune donnée disponible pour ce scénario"
                ),
            }
            for row in results
        ]


def get_models_for_departments(departments: list[str]) -> list[dict]:
    """
    Get models tested in selected departments (cascading filter).
    
    Args:
        departments: List of department names
        
    Returns:
        List of dicts: {
            "id": int,
            "name": str,
            "execution_count": int
        }
    """
    if not departments:
        return []
    
    with engine.connect() as conn:
        query = text("""
            SELECT
                m.id,
                m.nom,
                COUNT(DISTINCT e.id) as execution_count
            FROM modeles m
            JOIN executions e ON e.modele_id = m.id
            JOIN scenarios s ON s.id = e.scenario_id
            WHERE s.departement = ANY(:departments)
            GROUP BY m.id, m.nom
            ORDER BY execution_count DESC, m.nom
        """)
        
        results = conn.execute(query, {"departments": departments}).fetchall()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "execution_count": row[2],
            }
            for row in results
        ]


def get_department_model_comparison(
    department: str,
) -> pd.DataFrame:
    """
    Get all models and their metrics for multi-metric comparison (radar chart).
    
    Args:
        department: Department name
        
    Returns:
        DataFrame with columns:
        - model_name: str
        - faithfulness: float (0-1)
        - answer_relevancy: float (0-1)
        - context_precision: float (0-1)
        - context_recall: float (0-1)
        - global_score: float (average of 4 metrics)
        - avg_latency: float (seconds)
        - execution_count: int
    """
    with engine.connect() as conn:
        query = text("""
            SELECT
                m.nom as model_name,
                AVG(CASE WHEN f.critere = 'faithfulness' THEN f.note END) as faithfulness,
                AVG(CASE WHEN ar.critere = 'answer_relevancy' THEN ar.note END) as answer_relevancy,
                AVG(CASE WHEN cp.critere = 'context_precision' THEN cp.note END) as context_precision,
                AVG(CASE WHEN cr.critere = 'context_recall' THEN cr.note END) as context_recall,
                AVG(e.latence_secondes) as avg_latency,
                COUNT(DISTINCT e.id) as execution_count
            FROM executions e
            JOIN modeles m ON m.id = e.modele_id
            JOIN scenarios s ON s.id = e.scenario_id
            LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.is_legacy = FALSE
            LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.is_legacy = FALSE
            LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.is_legacy = FALSE
            LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.is_legacy = FALSE
            WHERE s.departement = :department
            GROUP BY m.nom
            ORDER BY (
                COALESCE(AVG(CASE WHEN f.critere = 'faithfulness' THEN f.note END), 0) + 
                COALESCE(AVG(CASE WHEN ar.critere = 'answer_relevancy' THEN ar.note END), 0) + 
                COALESCE(AVG(CASE WHEN cp.critere = 'context_precision' THEN cp.note END), 0) + 
                COALESCE(AVG(CASE WHEN cr.critere = 'context_recall' THEN cr.note END), 0)
            ) / 4.0 DESC
        """)
        
        df = pd.read_sql(query, conn, params={"department": department})
        
        # Compute global score
        ragas_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        df["global_score"] = df[ragas_cols].mean(axis=1).round(3)
        
        return df


def get_department_leaderboard(
    departments: list[str] | None = None,
) -> pd.DataFrame:
    """
    Get per-department recommendation leaderboard (ranked models).
    
    Args:
        departments: Optional list to filter specific departments. If None, all departments.
        
    Returns:
        DataFrame with columns:
        - rank: int (1, 2, 3, ...)
        - departement: str
        - model_name: str
        - global_score: float
        - execution_count: int
        - faithfulness: float
        - answer_relevancy: float
        - context_precision: float
        - context_recall: float
    """
    where_clause = ""
    params = {}
    
    if departments:
        where_clause = "WHERE s.departement = ANY(:departments)"
        params["departments"] = departments
    
    with engine.connect() as conn:
        query = text(f"""
            WITH scored_models AS (
                SELECT
                    s.departement,
                    m.nom as model_name,
                    AVG(CASE WHEN f.critere = 'faithfulness' THEN f.note END) as faithfulness,
                    AVG(CASE WHEN ar.critere = 'answer_relevancy' THEN ar.note END) as answer_relevancy,
                    AVG(CASE WHEN cp.critere = 'context_precision' THEN cp.note END) as context_precision,
                    AVG(CASE WHEN cr.critere = 'context_recall' THEN cr.note END) as context_recall,
                    COUNT(DISTINCT e.id) as execution_count
                FROM executions e
                JOIN modeles m ON m.id = e.modele_id
                JOIN scenarios s ON s.id = e.scenario_id
                LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.is_legacy = FALSE
                LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.is_legacy = FALSE
                LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.is_legacy = FALSE
                LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.is_legacy = FALSE
                {where_clause}
                GROUP BY s.departement, m.nom
            )
            SELECT
                ROW_NUMBER() OVER (PARTITION BY departement ORDER BY 
                    (COALESCE(faithfulness, 0) + COALESCE(answer_relevancy, 0) + 
                     COALESCE(context_precision, 0) + COALESCE(context_recall, 0)) / 4.0 DESC
                ) as rank,
                departement,
                model_name,
                (COALESCE(faithfulness, 0) + COALESCE(answer_relevancy, 0) + 
                 COALESCE(context_precision, 0) + COALESCE(context_recall, 0)) / 4.0 as global_score,
                execution_count,
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            FROM scored_models
            ORDER BY departement, rank
        """)
        
        df = pd.read_sql(query, conn, params=params if params else None)
        
        return df
