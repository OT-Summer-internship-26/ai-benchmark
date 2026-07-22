from src.rag.vector_store import init_vector_table, search_similar
from src.rag.retriever import index_pdf

if __name__ == "__main__":
    init_vector_table()

    index_pdf("data/documents_departements/rh/guide_recrutement.pdf", "RH & Communication")
    index_pdf("data/documents_departements/rh/guide_entretien_de_recrutement.pdf", "RH & Communication")
    index_pdf("data/documents_departements/rh/guide_pedagogique_recrutement.pdf", "RH & Communication")

    print("\n=== Question 1 : Comment rédiger une fiche de poste ? ===")
    resultats1 = search_similar("Comment rédiger une fiche de poste efficace ?", "RH & Communication", top_k=3)
    for i, r in enumerate(resultats1, 1):
        print(f"\n[{i}] {r}")

    print("\n\n=== Question 2 : Comment hiérarchiser les compétences en entretien ? ===")
    resultats2 = search_similar("Comment hiérarchiser les compétences lors d'un entretien de recrutement ?", "RH & Communication", top_k=3)
    for i, r in enumerate(resultats2, 1):
        print(f"\n[{i}] {r}")