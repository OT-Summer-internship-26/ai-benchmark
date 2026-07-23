from pypdf import PdfReader

def extract_text_from_pdf(filepath: str) -> str:
    """Extrait tout le texte brut d'un fichier PDF, nettoyé des caractères problématiques."""
    reader = PdfReader(filepath)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    # Supprime les caractères NUL et autres caractères de contrôle problématiques
    full_text = full_text.replace("\x00", "")
    
    return full_text