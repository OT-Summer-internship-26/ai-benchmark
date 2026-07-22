from src.rag.document_loader import chunk_text
from src.rag.pdf_loader import extract_text_from_pdf
from src.rag.vector_store import add_document_chunk

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