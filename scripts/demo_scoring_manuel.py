from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    question = "Comment rédiger une fiche de poste efficace ?"
    departement = "RH & Communication"

    chunks = search_similar(question, departement, top_k=3)
    reponse = generate_response(question, chunks)

    print(f"Question : {question}")
    print(f"\nRéponse générée :\n{reponse}")

    print("\n--- Grille d'évaluation manuelle ---")
    print("Pertinence (1-5) : à noter manuellement en comparant la réponse à la question")
    print("Fidélité au contexte (1-5) : vérifier si tout vient bien des chunks affichés ci-dessus")
    print("Clarté (1-5) : évaluer la structure de la réponse")
    print("Respect de la langue (1-5) : vérifier la cohérence avec la langue de la question")