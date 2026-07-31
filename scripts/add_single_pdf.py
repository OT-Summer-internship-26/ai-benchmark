from src.rag.retriever import index_pdf

if __name__ == "__main__":
    index_pdf(
        filepath="data/documents_departements/support_b2b/tr1915.pdf",
        departement="Réseau / Support Technique (NOC)"
    )