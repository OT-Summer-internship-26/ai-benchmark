import requests
import time
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.translation.translator import traduire_depuis_francais, detecter_arabe_tunisien
from src.utils.logger import setup_logger
from src.utils.exceptions import OllamaUnavailableException, LLMException
from src.utils.retry import retry_with_backoff
from src.observability.langfuse_client import trace_llm_call

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
def _call_ollama(model_name: str, prompt: str, metadata: dict = None) -> tuple[str, dict]:
    """
    Make a single call to Ollama with retry logic and Langfuse tracing.
    
    Args:
        model_name: Name of the model to use
        prompt: The prompt to send
        metadata: Optional metadata for Langfuse tracing
        
    Returns:
        Tuple of (response_text, usage_stats) where usage_stats contains:
            - prompt_tokens: Number of tokens in prompt (eval_count from Ollama)
            - completion_tokens: Number of tokens in completion (prompt_eval_count)
            - total_tokens: Total tokens
            - latency: Response latency in seconds
        
    Raises:
        OllamaUnavailableException: If Ollama is not available
        LLMException: If the LLM call fails
    """
    with trace_llm_call(
        name="ollama_generation",
        model=model_name,
        input_prompt=prompt,
        metadata=metadata or {},
    ) as trace:
        try:
            logger.debug(f"Calling Ollama model={model_name}")
            
            start_time = time.time()
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=OLLAMA_TIMEOUT
            )
            latency = time.time() - start_time
            
            # Check for HTTP errors
            if response.status_code == 404:
                raise LLMException(f"Model '{model_name}' not found in Ollama")
            
            response.raise_for_status()
            
            # Extract content and usage from response
            response_json = response.json()
            content = response_json.get("message", {}).get("content")
            if content is None:
                raise LLMException("Ollama response missing content field")
            
            # Extract token usage from Ollama response
            # Ollama returns: eval_count (output tokens), prompt_eval_count (input tokens)
            eval_count = response_json.get("eval_count", 0)  # completion tokens
            prompt_eval_count = response_json.get("prompt_eval_count", 0)  # prompt tokens
            total_tokens = eval_count + prompt_eval_count
            
            # Calculer un coût estimé (Ollama local = gratuit, mais on peut estimer
            # un coût équivalent pour comparaison avec les API payantes)
            # Approximation : $0.0002 par 1K tokens (équivalent GPT-3.5 turbo)
            estimated_cost = (total_tokens / 1000.0) * 0.0002
            
            usage_stats = {
                "prompt_tokens": prompt_eval_count,
                "completion_tokens": eval_count,
                "total_tokens": total_tokens,
                "latency": latency,
                "estimated_cost": estimated_cost,
            }
            
            # Enregistrer dans Langfuse
            trace.set_output(content)
            trace.set_usage(
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=total_tokens,
                total_cost=estimated_cost,
            )
            trace.set_metadata(latency_seconds=latency)
            
            logger.debug(
                f"Ollama response received ({len(content)} chars, "
                f"{total_tokens} tokens, {latency:.2f}s)"
            )
            return content, usage_stats
            
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
    Generate a multilingual response using Ollama (backward compatible - returns string).
    
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
    # Call the new function and discard usage stats for backward compatibility
    response, _ = generate_response_with_usage(question, context_chunks, model_name, metadata=None)
    return response


def generate_response_with_usage(
    question: str,
    context_chunks: list[str],
    model_name: str = "llama3.1:8b",
    metadata: dict = None,
) -> tuple[str, dict]:
    """
    Generate a multilingual response using Ollama with token usage tracking.
    
    Args:
        question: The question to answer
        context_chunks: RAG context chunks to use
        model_name: Ollama model name to use
        metadata: Optional metadata for Langfuse tracing (e.g., scenario_id, execution_id)
        
    Returns:
        Tuple of (response_text, usage_stats) where usage_stats contains:
            - prompt_tokens: Number of tokens in prompt
            - completion_tokens: Number of tokens in completion
            - total_tokens: Total tokens
            - latency: Response latency in seconds
            - estimated_cost: Estimated cost in USD
        
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

        # Call Ollama with retry logic and get usage stats
        content, usage_stats = _call_ollama(model_name, prompt, metadata=metadata)
        
        # If question is in French, return as-is
        if langue_de_la_question == "fr":
            return content, usage_stats
        
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
                translated = traduire_depuis_francais(content, langue_de_la_question)
                return translated, usage_stats
            except Exception as e:
                logger.warning(f"Translation failed: {str(e)}, returning French response")
                return content, usage_stats
        
        return content, usage_stats
        
    except OllamaUnavailableException:
        raise
    except LLMException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_response_with_usage: {str(e)}")
        raise LLMException(f"Failed to generate response: {str(e)}")
