from src.rag.vector_store import search_similar
from src.rag.retriever import index_pdf
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    # 1. Indexer les 5 PDF du département Productivité Personnelle
    index_pdf("data/documents_departements/productivite/Comment-rediger-un-compte-rendu-de-reunion.pdf", "Productivité Personnelle")
    index_pdf("data/documents_departements/productivite/fiche-methode-rediger-un-compterendu.pdf", "Productivité Personnelle")
    index_pdf("data/documents_departements/productivite/20-Bonnes-pratiques-de-veille.pdf", "Productivité Personnelle")
    index_pdf("data/documents_departements/productivite/GuideCourriel_web_-3.pdf", "Productivité Personnelle")
    index_pdf("data/documents_departements/productivite/Guide-pratique-v5.pdf", "Productivité Personnelle")

    # 2. Test de retrieval : compte-rendu de réunion
    print("\n=== Question 1 : Comment structurer un compte-rendu de réunion ? ===")
    resultats1 = search_similar("Comment structurer un compte-rendu de réunion efficace ?", "Productivité Personnelle", top_k=3)
    for i, r in enumerate(resultats1, 1):
        print(f"\n[{i}] {r[:300]}")

    # 3. Test de retrieval : veille concurrentielle
    print("\n\n=== Question 2 : Comment mettre en place une veille concurrentielle ? ===")
    resultats2 = search_similar("Quelles sont les bonnes pratiques pour mettre en place une veille concurrentielle ?", "Productivité Personnelle", top_k=3)
    for i, r in enumerate(resultats2, 1):
        print(f"\n[{i}] {r[:300]}")

    # 4. Test de retrieval : gestion emails
    print("\n\n=== Question 3 : Comment prioriser mes emails ? ===")
    resultats3 = search_similar("Comment gérer et prioriser efficacement une boîte mail saturée ?", "Productivité Personnelle", top_k=3)
    for i, r in enumerate(resultats3, 1):
        print(f"\n[{i}] {r[:300]}")

    # 5. Test complet avec génération LLM
    print("\n\n=== Test génération complète ===")
    question = "Comment rédiger un bon compte-rendu de réunion ?"
    chunks = search_similar(question, "Productivité Personnelle", top_k=3)
    reponse = generate_response(question, chunks)
    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")