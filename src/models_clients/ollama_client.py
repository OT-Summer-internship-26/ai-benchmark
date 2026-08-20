import requests
import time
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.translation.translator import traduire_depuis_francais, detecter_arabe_tunisien
from src.utils.logger import setup_logger
from src.utils.exceptions import OllamaUnavailableException, LLMException
from src.utils.retry import retry_with_backoff

logger = setup_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_TIMEOUT = 180  # seconds
OLLAMA_CONNECT_TIMEOUT = 5  # seconds

LANGUES_SUPPORTEES = {"fr", "en", "ar", "tn"}
LANGUE_LABELS = {
    "fr": "français",
    "en": "English",
    "ar": "arabe",
    "tn": "tunisien",
}


def check_ollama_health() -> bool:
    """
    Check if Ollama service is available and responding.
    
    Returns:
        True if Ollama is available, False otherwise
    """
    try:
        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=OLLAMA_CONNECT_TIMEOUT
        )
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False
    except Exception:
        return False


def _detecter_langue(question: str) -> str:
    """Detect language of the question with fallback."""
    try:
        langue = detect(question)
        if langue == "ar" and detecter_arabe_tunisien(question):
            return "tn"
        return langue if langue in LANGUES_SUPPORTEES else "en"
    except (Exception, LangDetectException):
        logger.debug("Language detection failed, defaulting to French")
        return "fr"


@retry_with_backoff(
    max_attempts=3,
    initial_delay=2.0,
    backoff_factor=2.0,
    max_delay=30.0,
    exceptions=(requests.Timeout, requests.ConnectionError)
)
def _call_ollama(model_name: str, prompt: str) -> str:
    """
    Make a single call to Ollama with retry logic.
    
    Args:
        model_name: Name of the model to use
        prompt: The prompt to send
        
    Returns:
        Generated response text
        
    Raises:
        OllamaUnavailableException: If Ollama is not available
        LLMException: If the LLM call fails
    """
    try:
        logger.debug(f"Calling Ollama model={model_name}")
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        # Check for HTTP errors
        if response.status_code == 404:
            raise LLMException(f"Model '{model_name}' not found in Ollama")
        
        response.raise_for_status()
        
        # Extract content from response
        content = response.json().get("message", {}).get("content")
        if content is None:
            raise LLMException("Ollama response missing content field")
        
        logger.debug(f"Ollama response received ({len(content)} chars)")
        return content
        
    except requests.ConnectionError as e:
        logger.error(f"Ollama connection failed: {str(e)}")
        raise OllamaUnavailableException(
            f"Could not connect to Ollama at {OLLAMA_URL}. "
            "Ensure Ollama is running: ollama serve"
        )
    except requests.Timeout as e:
        logger.error(f"Ollama request timed out: {str(e)}")
        raise LLMException(f"Ollama timeout after {OLLAMA_TIMEOUT}s")
    except requests.HTTPError as e:
        logger.error(f"Ollama HTTP error: {str(e)}")
        raise LLMException(f"Ollama HTTP error: {response.status_code}")
    except ValueError as e:
        logger.error(f"Ollama response parsing error: {str(e)}")
        raise LLMException(f"Invalid Ollama response: {str(e)}")


def generate_response(
    question: str,
    context_chunks: list[str],
    model_name: str = "llama3.1:8b"
) -> str:
    """
    Generate a multilingual response using Ollama.
    
    Args:
        question: The question to answer
        context_chunks: RAG context chunks to use
        model_name: Ollama model name to use
        
    Returns:
        Generated response in appropriate language
        
    Raises:
        OllamaUnavailableException: If Ollama is not available
        LLMException: If the LLM call fails after retries
    """
    # Check Ollama health first
    if not check_ollama_health():
        logger.error("Ollama health check failed")
        raise OllamaUnavailableException(
            f"Ollama is not available at {OLLAMA_URL}. "
            "Start Ollama with: ollama serve"
        )
    
    try:
        # Detect question language
        langue_de_la_question = _detecter_langue(question)
        label_langue = LANGUE_LABELS.get(langue_de_la_question, "anglais")
        
        # Build context
        context = "\n\n---\n\n".join(context_chunks)
        
        # Create prompt
        prompt = f"""Tu es un assistant professionnel pour Ooredoo.
Réponds en {label_langue} à la question suivante, en te basant UNIQUEMENT sur le contexte fourni.

Question : {question}

Contexte :
{context}

INSTRUCTIONS :
1. Réponds en {label_langue} uniquement.
2. Va directement au contenu, sans introduction ni préambule.
3. Ne répète JAMAIS la question dans ta réponse.
4. Structure la réponse en points numérotés ou à puces si nécessaire.
5. Si l'information n'est pas dans le contexte, dis-le en une phrase courte."""

        # Call Ollama with retry logic
        content = _call_ollama(model_name, prompt)
        
        # If question is in French, return as-is
        if langue_de_la_question == "fr":
            return content
        
        # Otherwise, detect response language and translate if needed
        try:
            langue_reponse = detect(content)
        except (Exception, LangDetectException):
            logger.debug("Response language detection failed, assuming French")
            langue_reponse = "fr"
        
        # Translate French response to question language if needed
        if langue_reponse == "fr" and langue_de_la_question in {"en", "ar", "tn"}:
            logger.debug(f"Translating response to {langue_de_la_question}")
            try:
                return traduire_depuis_francais(content, langue_de_la_question)
            except Exception as e:
                logger.warning(f"Translation failed: {str(e)}, returning French response")
                return content
        
        return content
        
    except OllamaUnavailableException:
        raise
    except LLMException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_response: {str(e)}")
        raise LLMException(f"Failed to generate response: {str(e)}")
