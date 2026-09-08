# ============================================================================
# IMPORTANT: SSL/TLS patching MUST come before any httpx imports
# ============================================================================
import os
import warnings
import certifi

# Set SSL environment variables for urllib, requests, etc.
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

# Suppress SSL warnings (verification disabled for corporate MITM inspection compatibility)
warnings.filterwarnings('ignore')

# CRITICAL: Patch httpx BEFORE sentence_transformers imports it
import httpx

_original_httpx_client_init = httpx.Client.__init__

def _patched_httpx_client_init(self, *args, **kwargs):
    """Patch httpx.Client to disable SSL verification for corporate environments."""
    kwargs['verify'] = False
    return _original_httpx_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_httpx_client_init

# Also patch AsyncClient for async operations
_original_httpx_async_init = httpx.AsyncClient.__init__

def _patched_httpx_async_init(self, *args, **kwargs):
    """Patch httpx.AsyncClient to disable SSL verification."""
    kwargs['verify'] = False
    return _original_httpx_async_init(self, *args, **kwargs)

httpx.AsyncClient.__init__ = _patched_httpx_async_init

# NOW safe to import sentence_transformers (uses our patched httpx)
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
