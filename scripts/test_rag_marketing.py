from src.rag.vector_store import search_similar
from src.rag.retriever import index_pdf

if __name__ == "__main__":
    index_pdf("data/documents_departements/marketing/20-conseils-pour-rédiger-un-texte-publicitaire.pdf", "Marketing & Digital")
    index_pdf("data/documents_departements/marketing/Livre-blanc-SMS_Le-SMS-pour-les-agences-de-communication.pdf", "Marketing & Digital")
    index_pdf("data/documents_departements/marketing/Social-media-guidelinesFR-1.pdf", "Marketing & Digital")
    index_pdf("data/documents_departements/marketing/guide_redaction_web.pdf", "Marketing & Digital")
    index_pdf("data/documents_departements/marketing/guide_seo_yoast.pdf", "Marketing & Digital")

    print("\n=== Question 1 : Comment rédiger un bon SMS publicitaire ? ===")
    resultats1 = search_similar("Comment rédiger un bon message SMS publicitaire ?", "Marketing & Digital", top_k=3)
    for i, r in enumerate(resultats1, 1):
        print(f"\n[{i}] {r}")

    print("\n\n=== Question 2 : Comment optimiser un article de blog pour le SEO ? ===")
    resultats2 = search_similar("Comment optimiser un article de blog pour le référencement SEO ?", "Marketing & Digital", top_k=3)
    for i, r in enumerate(resultats2, 1):
        print(f"\n[{i}] {r}")