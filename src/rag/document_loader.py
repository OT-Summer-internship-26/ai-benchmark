import re


def load_document(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Découpe le texte en respectant les paragraphes/phrases autant que possible."""
    
    # 1. Split en paragraphes (double saut de ligne ou saut de ligne simple)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Si le paragraphe seul dépasse chunk_size, on le découpe par phrases
        if len(para) > chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= chunk_size:
                    current_chunk += " " + sentence
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    # overlap : on garde la fin du chunk précédent
                    current_chunk = current_chunk[-overlap:] + " " + sentence
        else:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += "\n" + para
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = current_chunk[-overlap:] + "\n" + para
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return [c.strip() for c in chunks if len(c.strip()) > 30]  # filtre les chunks trop petits/vides