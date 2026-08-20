import time
import requests
from src.models_clients.ollama_client import generate_response as generate_response_ollama
from src.models_clients.gemini_client import generate_response as generate_response_gemini
from src.database.connection import engine
from sqlalchemy import text
from src.utils.logger import setup_logger
from src.utils.retry import retry_with_backoff
from src.utils.exceptions import DatabaseException, LLMException, ModelNotFoundError, OllamaUnavailableException

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Registre des modèles supportés par le pipeline.
#
# Chaque entrée précise :
#   - "id"       : id en base (table modeles)
#   - "provider" : "ollama" (LLM local) ou "gemini" (appel API)
#
# Ollama nécessite un service local qui tourne (health check avant appel).
# Gemini est un appel API distant, pas de health check préalable nécessaire —
# les erreurs API sont gérées directement par le retry/backoff.
# ---------------------------------------------------------------------------
MAPPING_MODELES = {
    "llama3.1:8b": {"id": 9, "provider": "ollama"},
    "mistral:7b": {"id": 10, "provider": "ollama"},
    "gemma2:9b": {"id": 11, "provider": "ollama"},
    "qwen2.5:7b": {"id": 12, "provider": "ollama"},
    "qwen3:8b": {"id": 13, "provider": "ollama"},
    "gemini-3.1-flash-lite": {"id": 14, "provider": "gemini"},
}


def _check_model_available(model_name: str) -> bool:
    """Check if Ollama is running and model is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model_name.split(":")[0]) for m in models)
    except requests.RequestException:
        raise OllamaUnavailableException("Ollama service is not available at http://localhost:11434")
    return False


@retry_with_backoff(
    max_attempts=3,
    initial_delay=2.0,
    exceptions=(requests.Timeout, requests.ConnectionError)
)
def _generate_response_ollama_with_retry(question: str, context_chunks: list[str], model_name: str) -> str:
    """Generate response with retry logic for transient network failures (Ollama)."""
    return generate_response_ollama(
        question=question,
        context_chunks=context_chunks,
        model_name=model_name
    )


@retry_with_backoff(
    max_attempts=3,
    initial_delay=2.0,
    exceptions=(Exception,)  # les erreurs API Gemini (quota, 5xx, réseau) sont génériques côté SDK
)
def _generate_response_gemini_with_retry(question: str, context_chunks: list[str]) -> str:
    """Generate response with retry logic for transient failures (Gemini API)."""
    return generate_response_gemini(
        question=question,
        context_chunks=context_chunks,
    )


def agent_executeur(state: dict) -> dict:
    """
    Pour chaque scénario × chaque modèle :
    - Valide que le modèle existe dans MAPPING_MODELES
    - Route vers le bon provider (Ollama local ou API Gemini)
    - Génère une réponse via le pipeline RAG + LLM
    - Mesure la latence
    - Enregistre dans la table executions avec gestion appropriée des erreurs
    """
    logger.info(f"[EXECUTEUR] Lancement du benchmark...")
    logger.info(f"  {len(state['scenarios'])} scénarios × {len(state['model_names'])} modèles = {len(state['scenarios']) * len(state['model_names'])} exécutions")

    executions = []
    erreurs = state.get("erreurs", [])

    # Validate models exist in mapping
    invalid_models = [m for m in state['model_names'] if m not in MAPPING_MODELES]
    if invalid_models:
        for model in invalid_models:
            msg = f"Modèle '{model}' non trouvé dans le mapping. Modèles disponibles: {', '.join(MAPPING_MODELES.keys())}"
            erreurs.append(msg)
            logger.error(msg)

    try:
        with engine.begin() as conn:  # Automatic transaction management
            for scenario in state["scenarios"]:
                for nom_modele in state["model_names"]:

                    if nom_modele not in MAPPING_MODELES:
                        continue

                    modele_info = MAPPING_MODELES[nom_modele]
                    modele_id = modele_info["id"]
                    provider = modele_info["provider"]
                    logger.info(f"\n  -> Scenario [{scenario['id']}] {scenario['nom_cas_usage']} | Modele : {nom_modele} ({provider})")

                    try:
                        if provider == "ollama":
                            # Verify Ollama model is available before attempting
                            if not _check_model_available(nom_modele):
                                msg = f"Modèle {nom_modele} n'est pas disponible dans Ollama"
                                logger.warning(msg)
                                erreurs.append(msg)
                                continue

                            debut = time.time()
                            reponse = _generate_response_ollama_with_retry(
                                question=scenario["prompt"],
                                context_chunks=scenario["chunks_rag"],
                                model_name=nom_modele
                            )
                            latence = time.time() - debut

                        elif provider == "gemini":
                            # Pas de health check préalable : on tente l'appel directement,
                            # les erreurs (clé API invalide, quota, réseau) sont gérées par le retry.
                            debut = time.time()
                            reponse = _generate_response_gemini_with_retry(
                                question=scenario["prompt"],
                                context_chunks=scenario["chunks_rag"],
                            )
                            latence = time.time() - debut

                        else:
                            msg = f"Provider inconnu '{provider}' pour le modèle {nom_modele}"
                            erreurs.append(msg)
                            logger.error(msg)
                            continue

                        logger.info(f"     OK - Reponse generee en {latence:.2f}s")

                        # Use proper parameterized query
                        result = conn.execute(
                            text("""
                                INSERT INTO executions 
                                (scenario_id, modele_id, reponse_generee, latence_secondes, cout_estime, date_execution)
                                VALUES (:scenario_id, :modele_id, :reponse, :latence, :cout, NOW())
                                RETURNING id
                            """),
                            {
                                "scenario_id": scenario["id"],
                                "modele_id": modele_id,
                                "reponse": reponse,
                                "latence": latence,
                                "cout": 0.0,
                            }
                        )
                        execution_id = result.fetchone()[0]

                        executions.append({
                            "execution_id": execution_id,
                            "scenario_id": scenario["id"],
                            "scenario_nom": scenario["nom_cas_usage"],
                            "modele": nom_modele,
                            "reponse": reponse,
                            "latence": latence,
                        })

                    except OllamaUnavailableException as e:
                        msg = f"Ollama unavailable for scenario {scenario['id']}: {str(e)}"
                        erreurs.append(msg)
                        logger.error(msg)
                    except LLMException as e:
                        msg = f"LLM error for scenario {scenario['id']} / modèle {nom_modele}: {str(e)}"
                        erreurs.append(msg)
                        logger.error(msg)
                    except Exception as e:
                        msg = f"Erreur scénario {scenario['id']} / modèle {nom_modele} ({provider}): {str(e)}"
                        erreurs.append(msg)
                        logger.error(msg)

    except Exception as e:
        msg = f"Critical error in executeur: {str(e)}"
        erreurs.append(msg)
        logger.error(msg)
        raise DatabaseException(msg)

    logger.info(f"[EXECUTEUR] {len(executions)} exécutions terminées, {len(erreurs)} erreurs.")

    return {
        **state,
        "executions": executions,
        "erreurs": erreurs,
    }