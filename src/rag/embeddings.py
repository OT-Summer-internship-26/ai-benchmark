from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Lazy-load model to avoid SSL issues at import time
_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model

def get_embedding(text: str) -> list[float]:
    """Get embedding for text. Model loads on first use."""
    try:
        model = _get_model()
        return model.encode(text).tolist()
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        raise