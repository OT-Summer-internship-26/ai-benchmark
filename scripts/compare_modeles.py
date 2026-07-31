import time
from src.rag.vector_store import search_similar
from src.models_clients.ollama_client import generate_response
from src.database.connection import engine
from sqlalchemy import text

MODELES_A_TESTER = {
    "llama3.1:8b": 9,
    "mistral:7b": 10,
    "gemma2:9b": 11,
    "qwen2.5:7b": 12,
}

# (scenario_id, question, département) — vérifie les scenario_id avec afficher_scenarios.py
SCENARIOS_A_TESTER = [
    (1, "Comment rédiger une fiche de poste efficace ?", "RH & Communication"),
    (8, "Quelles sont les meilleures pratiques pour documenter une API ?", "IT & Architecture"),
    (11, "Quelles sont les étapes pour résoudre une panne de ligne dédiée ?", "Réseau / Support Technique (NOC)"),
]

with engine.connect() as conn:
    for scenario_id, question, departement in SCENARIOS_A_TESTER:
        print(f"\n{'#'*70}")
        print(f"SCÉNARIO {scenario_id} — {departement}")
        print(f"QUESTION : {question}")
        print(f"{'#'*70}")

        chunks = search_similar(question, departement, top_k=8)

        for nom_modele, modele_id in MODELES_A_TESTER.items():
            print(f"\n{'='*70}")
            print(f"MODÈLE : {nom_modele}")
            print(f"{'='*70}")

            debut = time.time()
            reponse = generate_response(question, chunks, model_name=nom_modele)
            duree = time.time() - debut

            print(f"Temps de réponse : {duree:.2f}s\n")
            print(reponse)

            conn.execute(
                text("""
                    INSERT INTO executions (scenario_id, modele_id, reponse_generee, latence_secondes, cout_estime, date_execution)
                    VALUES (:scenario_id, :modele_id, :reponse, :latence, :cout, NOW())
                """),
                {
                    "scenario_id": scenario_id,
                    "modele_id": modele_id,
                    "reponse": reponse,
                    "latence": duree,
                    "cout": 0.0,
                }
            )
            conn.commit()
            print("→ Résultat enregistré dans executions.")