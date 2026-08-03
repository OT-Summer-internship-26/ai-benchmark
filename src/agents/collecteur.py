from src.database.connection import engine
from src.rag.vector_store import search_similar
from sqlalchemy import text


def agent_collecteur(state: dict) -> dict:
    """
    Récupère les scénarios demandés depuis la base de données
    et les chunks RAG correspondants pour chaque scénario.
    """
    print(f"\n[COLLECTEUR] Récupération de {len(state['scenario_ids'])} scénarios...")

    scenarios = []
    erreurs = state.get("erreurs", [])

    with engine.connect() as conn:
        for scenario_id in state["scenario_ids"]:
            result = conn.execute(
                text("SELECT * FROM scenarios WHERE id = :id"),
                {"id": scenario_id}
            )
            row = result.mappings().fetchone()

            if not row:
                erreurs.append(f"Scénario {scenario_id} introuvable en base.")
                continue

            scenario = dict(row)

            # Récupération des chunks RAG pour ce scénario
            try:
                chunks = search_similar(
                    query=scenario["prompt"],
                    departement=scenario["departement"],
                    top_k=8
                )
                scenario["chunks_rag"] = chunks
                print(f"  ✓ Scénario {scenario_id} ({scenario['nom_cas_usage']}) — {len(chunks)} chunks RAG récupérés")
            except Exception as e:
                erreurs.append(f"Erreur RAG pour scénario {scenario_id}: {str(e)}")
                scenario["chunks_rag"] = []

            scenarios.append(scenario)

    print(f"[COLLECTEUR] {len(scenarios)} scénarios collectés.")

    return {
        **state,
        "scenarios": scenarios,
        "erreurs": erreurs,
    }