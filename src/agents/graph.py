from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional

from src.agents.collecteur import agent_collecteur
from src.agents.executeur import agent_executeur
from src.agents.evaluateur import agent_evaluateur
from src.agents.consolidateur import agent_consolidateur


# État partagé entre tous les agents
class BenchmarkState(TypedDict):
    scenario_ids: List[int]
    model_names: List[str]
    scenarios: List[dict]
    executions: List[dict]
    scores: List[dict]
    rapport: Optional[dict]
    erreurs: List[str]


def creer_graphe_benchmark():
    """Crée et compile le graphe LangGraph du pipeline benchmark."""

    graphe = StateGraph(BenchmarkState)

    # Ajout des noeuds (un noeud = un agent)
    graphe.add_node("collecteur", agent_collecteur)
    graphe.add_node("executeur", agent_executeur)
    graphe.add_node("evaluateur", agent_evaluateur)
    graphe.add_node("consolidateur", agent_consolidateur)

    # Définition du flux : point d'entrée → enchaînement → fin
    graphe.set_entry_point("collecteur")
    graphe.add_edge("collecteur", "executeur")
    graphe.add_edge("executeur", "evaluateur")
    graphe.add_edge("evaluateur", "consolidateur")
    graphe.add_edge("consolidateur", END)

    return graphe.compile()


# Instance globale du graphe — importable depuis n'importe où
benchmark_graph = creer_graphe_benchmark()