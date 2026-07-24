from src.rag.vector_store import search_similar
from src.rag.retriever import index_pdf
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    # 1. Indexer les 3 PDF du département Réseau/Support B2B
    index_pdf("data/documents_departements/support_b2b/guide-operateurs-declaration-incidents-reseaux.pdf", "Réseau / Support Technique (NOC)")
    index_pdf("data/documents_departements/support_b2b/tr1907.pdf", "Réseau / Support Technique (NOC)")
    index_pdf("data/documents_departements/support_b2b/ITSM-Incident-Process-Guide.pdf", "Réseau / Support Technique (NOC)")

    # 2. Test de retrieval : déclaration d'incidents réseau
    print("\n=== Question 1 : Comment déclarer un incident réseau grave ? ===")
    resultats1 = search_similar("Comment déclarer un incident affectant un réseau de télécommunications ?", "Réseau / Support Technique (NOC)", top_k=3)
    for i, r in enumerate(resultats1, 1):
        print(f"\n[{i}] {r[:300]}")

    # 3. Test de retrieval : diagnostic technique
    print("\n\n=== Question 2 : Comment diagnostiquer une panne de liaison ? ===")
    resultats2 = search_similar("Comment diagnostiquer et résoudre une panne de connexion réseau ?", "Réseau / Support Technique (NOC)", top_k=3)
    for i, r in enumerate(resultats2, 1):
        print(f"\n[{i}] {r[:300]}")

    # 4. Test complet avec génération LLM
    print("\n\n=== Test génération complète ===")
    question = "Quelles sont les étapes prioritaires pour résoudre un incident de panne de ligne dédiée ?"
    chunks = search_similar(question, "Réseau / Support Technique (NOC)", top_k=3)
    reponse = generate_response(question, chunks)
    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")