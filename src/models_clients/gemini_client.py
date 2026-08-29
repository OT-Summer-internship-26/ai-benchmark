from google import genai
from src.config.settings import GEMINI_API_KEY
from src.observability.langfuse_client import trace_llm_call
import time

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_response(question: str, context_chunks: list[str]) -> str:
    """
    Generate a response using Gemini API (backward compatible - returns string).
    
    Args:
        question: The question to answer
        context_chunks: RAG context chunks to use
        
    Returns:
        Generated response text
    """
    # Call the new function and discard usage stats for backward compatibility
    response, _ = generate_response_with_usage(question, context_chunks, metadata=None)
    return response


def generate_response_with_usage(
    question: str,
    context_chunks: list[str],
    metadata: dict = None,
) -> tuple[str, dict]:
    """
    Generate a response using Gemini API with Langfuse tracing and usage tracking.
    
    Args:
        question: The question to answer
        context_chunks: RAG context chunks to use
        metadata: Optional metadata for Langfuse tracing
        
    Returns:
        Tuple of (response_text, usage_stats) where usage_stats contains:
            - prompt_tokens: Number of tokens in prompt
            - completion_tokens: Number of tokens in completion
            - total_tokens: Total tokens
            - latency: Response latency in seconds
            - estimated_cost: Estimated cost in USD (based on Gemini Flash pricing)
    """
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""Tu es un assistant professionnel pour Ooredoo. Réponds à la question 
en te basant UNIQUEMENT sur le contexte fourni ci-dessous.

RÈGLE IMPORTANTE SUR LA LANGUE : Détecte automatiquement la langue dans laquelle la 
question est posée, quelle que soit cette langue (français, anglais, arabe, espagnol, 
allemand, etc.), et réponds TOUJOURS dans cette même langue - même si le contexte 
fourni est rédigé dans une langue différente. Traduis mentalement les informations 
pertinentes du contexte avant de formuler ta réponse dans la langue de la question.

Si l'information n'est pas présente dans le contexte, dis-le clairement (dans la langue 
de la question) plutôt que d'inventer une réponse.

Contexte (langue potentiellement différente de la question) :
{context}

Question : {question}

Réponse (impérativement dans la même langue que la question ci-dessus) :"""

    with trace_llm_call(
        name="gemini_generation",
        model="gemini-3.1-flash-lite",
        input_prompt=prompt,
        metadata=metadata or {},
    ) as trace:
        start_time = time.time()
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
        latency = time.time() - start_time
        
        # Extract token usage from Gemini response
        # Gemini returns usage_metadata with prompt_token_count, candidates_token_count
        usage_metadata = getattr(response, 'usage_metadata', None)
        
        if usage_metadata:
            prompt_tokens = getattr(usage_metadata, 'prompt_token_count', 0)
            completion_tokens = getattr(usage_metadata, 'candidates_token_count', 0)
            total_tokens = getattr(usage_metadata, 'total_token_count', prompt_tokens + completion_tokens)
        else:
            # Fallback: estimate based on text length (rough approximation: 1 token ≈ 4 chars)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response.text) // 4
            total_tokens = prompt_tokens + completion_tokens
        
        # Calculer le coût estimé basé sur les tarifs Gemini Flash
        # Gemini 3.1 Flash-Lite: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
        input_cost = (prompt_tokens / 1_000_000) * 0.075
        output_cost = (completion_tokens / 1_000_000) * 0.30
        estimated_cost = input_cost + output_cost
        
        usage_stats = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency": latency,
            "estimated_cost": estimated_cost,
        }
        
        # Enregistrer dans Langfuse
        trace.set_output(response.text)
        trace.set_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            total_cost=estimated_cost,
        )
        trace.set_metadata(latency_seconds=latency)
        
        return response.text, usage_stats