import sys
import pathlib
import argparse

# Configure UTF-8 for console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
root_dir = pathlib.Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.rag.vector_store import init_vector_table
from src.rag.retriever import index_document, departement_deja_indexe
from src.database.connection import engine
from sqlalchemy import text

DEPARTEMENTS_DOCUMENTS = {
    "RH": [
        "data/documents_departements/rh/guide_recrutement.pdf",
        "data/documents_departements/rh/guide_entretien_de_recrutement.pdf",
        "data/documents_departements/rh/guide_pedagogique_recrutement.pdf",
        "data/documents_departements/rh/politique_conges.txt",
        "data/documents_departements/rh/reglement_interieur.txt",
    ],
    "Marketing & Digital": [
        "data/documents_departements/marketing/20-conseils-pour-rédiger-un-texte-publicitaire.pdf",
        "data/documents_departements/marketing/Livre-blanc-SMS_Le-SMS-pour-les-agences-de-communication.pdf",
        "data/documents_departements/marketing/Social-media-guidelinesFR-1.pdf",
        "data/documents_departements/marketing/guide_redaction_web.pdf",
        "data/documents_departements/marketing/guide_seo_yoast.pdf",
        "data/documents_departements/marketing/guide_marque.txt",
    ],
    "IT & Cybersécurité": [
        "data/documents_departements/it/best-practices-code-generation.pdf",
        "data/documents_departements/it/code_modernization_playbook.pdf",
        "data/documents_departements/it/GitHub-Modernizing-COBOL-with-GitHub-Copilot_Whitepaper-2024.pdf",
        "data/documents_departements/it/White_Paper-The_Definitive_Guide_to_Creating_API_Documentation.pdf",
        "data/documents_departements/support_b2b/guide-operateurs-declaration-incidents-reseaux.pdf",
        "data/documents_departements/support_b2b/tr1907.pdf",
        "data/documents_departements/support_b2b/ITSM-Incident-Process-Guide.pdf",
        "data/documents_departements/support_b2b/tr1915.pdf",
        "data/documents_departements/support_b2b/historique_incidents.txt",
    ],
    "Productivité & Transversal": [
        "data/documents_departements/productivite/Comment-rediger-un-compte-rendu-de-reunion.pdf",
        "data/documents_departements/productivite/fiche-methode-rediger-un-compterendu.pdf",
        "data/documents_departements/productivite/20-Bonnes-pratiques-de-veille.pdf",
        "data/documents_departements/productivite/GuideCourriel_web_-3.pdf",
        "data/documents_departements/productivite/Guide-pratique-v5.pdf",
    ],
    "Service Client": [
        "data/documents_departements/service_client/faq_clients.txt",
        "data/documents_departements/service_client/procedures_support_client.md",
        "data/documents_departements/service_client/catalogue_offres_tarifs.md",
        "data/documents_departements/service_client/guide_my_ooredoo_selfcare.md",
    ],
}


def reset_vector_table():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM documents_vectorises"))
        avant = result.scalar()
        conn.execute(text("DELETE FROM documents_vectorises"))
        conn.commit()
        print(f"🗑️ Table 'documents_vectorises' réinitialisée ({avant} anciens chunks supprimés).")


def run_ingestion(force_reset: bool = False):
    print("=== Initialisation de la table vectorielle ===")
    init_vector_table()

    if force_reset:
        reset_vector_table()

    total_chunks = 0
    for departement, files in DEPARTEMENTS_DOCUMENTS.items():
        print(f"\n=== Indexation : {departement} ===")

        if not force_reset and departement_deja_indexe(departement):
            print(f"⚠️  '{departement}' déjà indexé, ignoré. Utilisez --reset pour tout réindexer.")
            continue

        for filepath in files:
            doc_path = root_dir / filepath
            if not doc_path.exists():
                print(f"⚠️ Fichier introuvable : {filepath}")
                continue
            index_document(str(doc_path), departement)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT departement, COUNT(*) FROM documents_vectorises GROUP BY departement ORDER BY departement")
        )
        print("\n📊 Bilan des documents vectorisés par département :")
        for row in result:
            print(f"  - {row[0]} : {row[1]} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion vectorielle des documents métiers.")
    parser.add_argument("--reset", action="store_true", help="Vider la table avant de réindexer.")
    args = parser.parse_args()

    run_ingestion(force_reset=args.reset)