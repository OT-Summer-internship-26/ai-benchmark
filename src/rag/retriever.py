from src.rag.document_loader import chunk_text
from src.rag.pdf_loader import extract_text_from_pdf
from src.rag.vector_store import add_document_chunk
from src.database.connection import engine
from sqlalchemy import text

def departement_deja_indexe(departement: str) -> bool:
    """Vérifie si un département a déjà des données vectorisées en base."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM documents_vectorises WHERE departement = :dep"),
            {"dep": departement}
        )
        count = result.scalar()
        return count > 0

def index_pdf(filepath: str, departement: str):
    """Charge un PDF, extrait son texte, le découpe, et stocke chaque morceau vectorisé."""
    text_content = extract_text_from_pdf(filepath)

    if not text_content.strip():
        print(f"Attention : aucun texte extrait de {filepath}.")
        return

    chunks = chunk_text(text_content)

    for chunk in chunks:
        add_document_chunk(departement, chunk)

    print(f"{len(chunks)} chunks indexés depuis '{filepath}' pour le département '{departement}'.")

def index_pdf_safe(filepath: str, departement: str):
    """Version sécurisée : vérifie d'abord si le département est déjà indexé."""
    if departement_deja_indexe(departement):
        print(f"⚠️ '{departement}' est déjà indexé en base. Utilisez index_pdf() pour forcer la réindexation.")
        return
    index_pdf(filepath, departement)