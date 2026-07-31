import re
from pypdf import PdfReader

def extract_text_from_pdf(filepath: str) -> str:
    """Extrait tout le texte brut d'un fichier PDF, nettoyé des caractères problématiques."""
    reader = PdfReader(filepath)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    full_text = full_text.replace("\x00", "")
    full_text = clean_extracted_text(full_text)
    
    return full_text


def clean_extracted_text(text: str) -> str:
    """Corrige les problèmes courants d'extraction PDF : mots collés, ponctuation collée."""
    
    # Espace manquant après une virgule/point suivi directement d'une lettre
    text = re.sub(r'([,.;:!?])([A-Za-zÀ-ÿ])', r'\1 \2', text)
    
    # Minuscule suivie directement d'une majuscule sans espace
    text = re.sub(r'([a-zà-ÿ])([A-ZÀ-Ÿ])', r'\1 \2', text)
    
    # Espaces multiples réduits à un seul
    text = re.sub(r' {2,}', ' ', text)
    
    return text