from src.rag.document_loader import chunk_text
from src.rag.pdf_loader import extract_text_from_pdf
from src.rag.txt_loader import extract_text_from_txt
from src.rag.vector_store import add_document_chunk
from src.database.connection import engine
from sqlalchemy import text

def departement_deja_indexe(departement: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM documents_vectorises WHERE departement = :dep"),
            {"dep": departement}
        )
        return result.scalar() > 0

def index_document(filepath: str, departement: str):
    """Charge un document (PDF ou TXT), l'indexe."""
    if filepath.lower().endswith(".pdf"):
        text_content = extract_text_from_pdf(filepath)
    elif filepath.lower().endswith(".txt"):
        text_content = extract_text_from_txt(filepath)
    else:
        print(f"Format non supporté : {filepath}")
        return

    if not text_content.strip():
        print(f"Attention : fichier vide ou aucun texte extrait de {filepath}.")
        return

    chunks = chunk_text(text_content)
    for chunk in chunks:
        add_document_chunk(departement, chunk)

    print(f"{len(chunks)} chunks indexés depuis '{filepath}' pour le département '{departement}'.")

# garde index_pdf comme alias pour compatibilité avec ton code existant
def index_pdf(filepath: str, departement: str):
    index_document(filepath, departement)