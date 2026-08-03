import time
from src.models_clients.ollama_client import generate_response
from src.database.connection import engine
from sqlalchemy import text

# Mapping nom Ollama → id en base (table modeles)
MAPPING_MODELES = {
    "llama3.1:8b": 9,
    "mistral:7b": 10,
    "gemma2:9b": 11,
    "qwen2.5:7b": 12,
}


def agent_executeur(state: dict) -> dict:
    """
    Pour chaque scénario × chaque modèle :
    - Génère une réponse via le pipeline RAG + LLM
    - Mesure la latence
    - Enregistre dans la table executions
    """
    print(f"\n[EXECUTEUR] Lancement du benchmark...")
    print(f"  {len(state['scenarios'])} scénarios × {len(state['model_names'])} modèles = {len(state['scenarios']) * len(state['model_names'])} exécutions")

    executions = []
    erreurs = state.get("erreurs", [])

    with engine.connect() as conn:
        for scenario in state["scenarios"]:
            for nom_modele in state["model_names"]:

                modele_id = MAPPING_MODELES.get(nom_modele)
                if not modele_id:
                    erreurs.append(f"Modèle '{nom_modele}' non trouvé dans le mapping.")
                    continue

                print(f"\n  → Scénario [{scenario['id']}] {scenario['nom_cas_usage']} | Modèle : {nom_modele}")

                try:
                    debut = time.time()
                    reponse = generate_response(
                        question=scenario["prompt"],
                        context_chunks=scenario["chunks_rag"],
                        model_name=nom_modele
                    )
                    latence = time.time() - debut

                    print(f"     ✓ Réponse générée en {latence:.2f}s")

                    conn.execute(
                        text("""
                            INSERT INTO executions 
                            (scenario_id, modele_id, reponse_generee, latence_secondes, cout_estime, date_execution)
                            VALUES (:scenario_id, :modele_id, :reponse, :latence, :cout, NOW())
                        """),
                        {
                            "scenario_id": scenario["id"],
                            "modele_id": modele_id,
                            "reponse": reponse,
                            "latence": latence,
                            "cout": 0.0,
                        }
                    )
                    conn.commit()

                    executions.append({
                        "scenario_id": scenario["id"],
                        "scenario_nom": scenario["nom_cas_usage"],
                        "modele": nom_modele,
                        "reponse": reponse,
                        "latence": latence,
                    })

                except Exception as e:
                    erreurs.append(f"Erreur scénario {scenario['id']} / modèle {nom_modele}: {str(e)}")
                    print(f"     ✗ Erreur : {str(e)}")

    print(f"\n[EXECUTEUR] {len(executions)} exécutions terminées.")

    return {
        **state,
        "executions": executions,
        "erreurs": erreurs,
    }