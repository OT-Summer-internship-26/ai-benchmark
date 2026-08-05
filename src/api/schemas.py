"""Schémas Pydantic — requêtes et réponses de l'API benchmark."""

from typing import Optional
from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    """Corps de la requête POST /benchmark/run"""

    scenario_ids: Optional[list[int]] = Field(
        default=None,
        description="IDs de scénarios à exécuter. Si None, tous les scénarios de la base sont utilisés.",
    )
    model_names: Optional[list[str]] = Field(
        default=None,
        description="Noms des modèles à tester (ex: ['llama3.1:8b', 'mistral:7b']). "
        "Si None, tous les modèles Ollama installés sont utilisés.",
    )


class BenchmarkRunResponse(BaseModel):
    """Réponse renvoyée après l'exécution du graphe LangGraph."""

    status: str
    nb_scenarios: int
    nb_modeles: int
    nb_executions: int
    rapport: Optional[dict] = None
    erreurs: list[str] = []