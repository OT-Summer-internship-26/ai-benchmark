def extract_text_from_txt(filepath: str) -> str:
    """Extrait le texte brut d'un fichier .txt."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()