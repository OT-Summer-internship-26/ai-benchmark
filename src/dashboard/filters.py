"""
Filter logic for cascading department → scenario → model selection.

This module handles:
1. Getting all unique departments from database
2. Getting scenarios for a specific department
3. Getting models that were actually tested on a set of scenarios
4. Normalizing filter selections to handle string matching edge cases
"""

from src.database.connection import SessionLocal
from src.database.models import Scenario, Execution, Modele


def get_all_departments() -> list[str]:
    """
    Fetch all unique departments from scenarios table.
    
    Returns:
        List of department names, sorted alphabetically, with no duplicates.
    """
    db = SessionLocal()
    try:
        departments = (
            db.query(Scenario.departement)
            .distinct()
            .order_by(Scenario.departement)
            .all()
        )
        return [d[0] for d in departments if d[0]]  # Filter out None/empty
    finally:
        db.close()


def get_scenarios_by_department(department: str) -> list[dict]:
    """
    Fetch all scenarios belonging to a specific department.
    
    Args:
        department: Department name (exact match, case-sensitive)
        
    Returns:
        List of dicts: [{"id": int, "nom_cas_usage": str, "departement": str}, ...]
        Sorted by scenario name.
    """
    db = SessionLocal()
    try:
        scenarios = (
            db.query(Scenario)
            .filter(Scenario.departement == department)
            .order_by(Scenario.nom_cas_usage)
            .all()
        )
        return [
            {
                "id": s.id,
                "nom_cas_usage": s.nom_cas_usage,
                "departement": s.departement,
            }
            for s in scenarios
        ]
    finally:
        db.close()


def get_scenarios_for_departments(departments: list[str]) -> list[dict]:
    """
    Fetch all scenarios belonging to any department in the list.
    
    Args:
        departments: List of department names
        
    Returns:
        List of dicts: [{"id": int, "nom_cas_usage": str, "departement": str}, ...]
        Sorted by department, then scenario name.
    """
    if not departments:
        return []
    
    db = SessionLocal()
    try:
        scenarios = (
            db.query(Scenario)
            .filter(Scenario.departement.in_(departments))
            .order_by(Scenario.departement, Scenario.nom_cas_usage)
            .all()
        )
        return [
            {
                "id": s.id,
                "nom_cas_usage": s.nom_cas_usage,
                "departement": s.departement,
            }
            for s in scenarios
        ]
    finally:
        db.close()


def get_models_for_scenarios(scenario_ids: list[int]) -> list[dict]:
    """
    Fetch all models that were actually tested on at least one of the given scenarios.
    
    Args:
        scenario_ids: List of scenario IDs
        
    Returns:
        List of dicts: [{"id": int, "nom": str, "fournisseur": str, "version": str}, ...]
        Sorted by model name, deduplicated.
    """
    if not scenario_ids:
        return []
    
    db = SessionLocal()
    try:
        # Subquery: get execution_ids for the given scenario_ids
        # Then fetch distinct modele_ids for those executions
        models = (
            db.query(Modele)
            .join(Execution, Execution.modele_id == Modele.id)
            .filter(Execution.scenario_id.in_(scenario_ids))
            .distinct()
            .order_by(Modele.nom)
            .all()
        )
        return [
            {
                "id": m.id,
                "nom": m.nom,
                "fournisseur": m.fournisseur or "Unknown",
                "version": m.version or "Unknown",
            }
            for m in models
        ]
    finally:
        db.close()


def get_all_models() -> list[dict]:
    """
    Fetch all models from the database.
    
    Returns:
        List of dicts: [{"id": int, "nom": str, "fournisseur": str, "version": str}, ...]
        Sorted by model name.
    """
    db = SessionLocal()
    try:
        models = db.query(Modele).order_by(Modele.nom).all()
        return [
            {
                "id": m.id,
                "nom": m.nom,
                "fournisseur": m.fournisseur or "Unknown",
                "version": m.version or "Unknown",
            }
            for m in models
        ]
    finally:
        db.close()


def normalize_department_name(name: str) -> str:
    """
    Normalize a department name for consistent matching.
    
    Applies: strip whitespace, normalize accents if needed (placeholder for future).
    
    Args:
        name: Raw department name from filter/input
        
    Returns:
        Normalized department name
    """
    return name.strip() if name else ""


def normalize_scenario_name(name: str) -> str:
    """Normalize a scenario name for consistent matching."""
    return name.strip() if name else ""


def normalize_model_name(name: str) -> str:
    """Normalize a model name for consistent matching."""
    return name.strip() if name else ""
