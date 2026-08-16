from src.database.connection import engine
from src.rag.vector_store import search_similar
from sqlalchemy import text
from src.utils.logger import setup_logger
from src.utils.exceptions import RAGException, DatabaseException

logger = setup_logger(__name__)


def agent_collecteur(state: dict) -> dict:
    """
    Récupère les scénarios demandés depuis la base de données
    et les chunks RAG correspondants pour chaque scénario.
    """
    logger.info(f"[COLLECTEUR] Récupération de {len(state['scenario_ids'])} scénarios...")

    scenarios = []
    erreurs = state.get("erreurs", [])

    try:
        with engine.connect() as conn:
            for scenario_id in state["scenario_ids"]:
                try:
                    result = conn.execute(
                        text("SELECT * FROM scenarios WHERE id = :id"),
                        {"id": scenario_id}
                    )
                    row = result.mappings().fetchone()

                    if not row:
                        msg = f"Scénario {scenario_id} introuvable en base."
                        erreurs.append(msg)
                        logger.warning(msg)
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
                        logger.info(f"✓ Scénario {scenario_id} ({scenario['nom_cas_usage']}) — {len(chunks)} chunks RAG récupérés")
                    except RAGException as e:
                        msg = f"Erreur RAG pour scénario {scenario_id}: {str(e)}"
                        erreurs.append(msg)
                        logger.error(msg)
                        scenario["chunks_rag"] = []

                    scenarios.append(scenario)
                    
                except Exception as e:
                    msg = f"Erreur lors du traitement du scénario {scenario_id}: {str(e)}"
                    erreurs.append(msg)
                    logger.error(msg)
                    continue
    except Exception as e:
        msg = f"Erreur critique en collecteur: {str(e)}"
        erreurs.append(msg)
        logger.error(msg)
        raise DatabaseException(msg)

    logger.info(f"[COLLECTEUR] {len(scenarios)} scénarios collectés.")

    return {
        **state,
        "scenarios": scenarios,
        "erreurs": erreurs,
    }