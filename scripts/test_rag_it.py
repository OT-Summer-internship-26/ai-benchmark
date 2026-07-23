from src.rag.vector_store import search_similar
from src.rag.retriever import index_pdf
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    # 1. Indexer les 4 PDF du département IT
    index_pdf("data/documents_departements/it/best-practices-code-generation.pdf", "IT & Architecture")
    index_pdf("data/documents_departements/it/code_modernization_playbook.pdf", "IT & Architecture")
    index_pdf("data/documents_departements/it/GitHub-Modernizing-COBOL-with-GitHub-Copilot_Whitepaper-2024.pdf", "IT & Architecture")
    index_pdf("data/documents_departements/it/White_Paper-The_Definitive_Guide_to_Creating_API_Documentation.pdf", "IT & Architecture")

    # 2. Test de retrieval : génération de code
    print("\n=== Question 1 : Comment améliorer la génération de code par IA ? ===")
    resultats1 = search_similar("Comment améliorer la précision de la génération de code par un assistant IA ?", "IT & Architecture", top_k=3)
    for i, r in enumerate(resultats1, 1):
        print(f"\n[{i}] {r[:300]}")

    # 3. Test de retrieval : modernisation legacy
    print("\n\n=== Question 2 : Comment moderniser du code COBOL ? ===")
    resultats2 = search_similar("Comment migrer du code COBOL legacy vers un langage moderne ?", "IT & Architecture", top_k=3)
    for i, r in enumerate(resultats2, 1):
        print(f"\n[{i}] {r[:300]}")

    # 4. Test complet avec génération LLM (question en français, sources en anglais)
    print("\n\n=== Test génération complète (français) ===")
    question = "Quelles sont les meilleures pratiques pour documenter une API ?"
    chunks = search_similar(question, "IT & Architecture", top_k=3)
    reponse = generate_response(question, chunks)
    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")