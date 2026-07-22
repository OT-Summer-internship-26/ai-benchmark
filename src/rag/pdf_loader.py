from pypdf import PdfReader

def extract_text_from_pdf(filepath: str) -> str:
    """Extrait tout le texte brut d'un fichier PDF."""
    reader = PdfReader(filepath)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    return full_text