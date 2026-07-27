from src.rag.vector_store import init_vector_table
from src.rag.retriever import index_pdf, departement_deja_indexe

DEPARTEMENTS = {
    "RH & Communication": [
        "data/documents_departements/rh/guide_recrutement.pdf",
        "data/documents_departements/rh/guide_entretien_de_recrutement.pdf",
        "data/documents_departements/rh/guide_pedagogique_recrutement.pdf",
    ],
    "Marketing & Digital": [
        "data/documents_departements/marketing/20-conseils-pour-rédiger-un-texte-publicitaire.pdf",
        "data/documents_departements/marketing/Livre-blanc-SMS_Le-SMS-pour-les-agences-de-communication.pdf",
        "data/documents_departements/marketing/Social-media-guidelinesFR-1.pdf",
        "data/documents_departements/marketing/guide_redaction_web.pdf",
        "data/documents_departements/marketing/guide_seo_yoast.pdf",
    ],
    "IT & Architecture": [
        "data/documents_departements/it/best-practices-code-generation.pdf",
        "data/documents_departements/it/code_modernization_playbook.pdf",
        "data/documents_departements/it/GitHub-Modernizing-COBOL-with-GitHub-Copilot_Whitepaper-2024.pdf",
        "data/documents_departements/it/White_Paper-The_Definitive_Guide_to_Creating_API_Documentation.pdf",
    ],
    "Réseau / Support Technique (NOC)": [
        "data/documents_departements/support_b2b/guide-operateurs-declaration-incidents-reseaux.pdf",
        "data/documents_departements/support_b2b/tr1907.pdf",
        "data/documents_departements/support_b2b/ITSM-Incident-Process-Guide.pdf",
    ],
    "Productivité Personnelle": [
        "data/documents_departements/productivite/Comment-rediger-un-compte-rendu-de-reunion.pdf",
        "data/documents_departements/productivite/fiche-methode-rediger-un-compterendu.pdf",
        "data/documents_departements/productivite/20-Bonnes-pratiques-de-veille.pdf",
        "data/documents_departements/productivite/GuideCourriel_web_-3.pdf",
        "data/documents_departements/productivite/Guide-pratique-v5.pdf",
    ],
}

if __name__ == "__main__":
    print("=== Initialisation de la table vectorielle ===")
    init_vector_table()

    for departement, pdfs in DEPARTEMENTS.items():
        print(f"\n=== Indexation : {departement} ===")

        if departement_deja_indexe(departement):
            print(f"⚠️  Déjà indexé, ignoré. Supprimez manuellement si vous voulez réindexer.")
            continue

        for pdf in pdfs:
            index_pdf(pdf, departement)

    print("\n✅ Data prep terminée pour tous les départements.")