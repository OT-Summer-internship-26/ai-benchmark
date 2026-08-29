from groq import Groq
from langdetect import detect
from src.config.settings import GROQ_API_KEY
from src.observability.langfuse_client import trace_llm_call
import time

client = Groq(api_key=GROQ_API_KEY)

LANGUE_NOMS = {
    "fr": "français",
    "en": "anglais",
    "ar": "arabe",
    "es": "espagnol",
    "de": "allemand",
    "it": "italien",
}

def generate_response(question: str, context_chunks: list[str]) -> str:
    """
    Generate a response using Groq API (backward compatible - returns string).
    
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
    Generate a response using Groq API with Langfuse tracing and usage tracking.
    
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
            - estimated_cost: Always 0.0 for Groq (free tier)
    """
    context = "\n\n---\n\n".join(context_chunks)

    try:
        code_langue = detect(question)
        nom_langue = LANGUE_NOMS.get(code_langue, code_langue)
    except Exception:
        nom_langue = "français"

    prompt = f"""Tu es un assistant professionnel pour Ooredoo.

INSTRUCTION OBLIGATOIRE : Tu dois rédiger TOUTE ta réponse en {nom_langue.upper()}, 
et uniquement en {nom_langue.upper()}. Traduis absolument tous les mots, y compris les 
termes techniques (noms de sections, paramètres, exemples de code, mots-clés), sauf 
les noms propres de langages de programmation (Python, Java) qui peuvent rester tels 
quels. N'utilise AUCUN mot d'une autre langue que le {nom_langue}, même isolé.


Question : {question}

Réponds à cette question en te basant UNIQUEMENT sur le contexte fourni ci-dessous.

Contexte :
{context}

RAPPEL : Ta réponse complète doit être entièrement en {nom_langue.upper()}.

INSTRUCTIONS FINALES CRITIQUES :
1. Ne répète JAMAIS la question dans ta réponse.
2. Ne mentionne JAMAIS la langue utilisée.
3. Va directement au contenu de la réponse, sans préambule.
4. Réponds de façon concrète et actionnable : cite les exemples, outils, chiffres ou 
étapes précises du contexte plutôt que de rester générique.
5. Structure ta réponse en points numérotés ou à puces pour des étapes ou éléments 
multiples.
6. Si l'information demandée n'est pas dans le contexte, dis-le en une phrase courte, 
sans combler par des généralités.
7. N'insère jamais un mot isolé d'une langue différente de {nom_langue} (pas de mélange, 
même pour un seul terme)."""

    with trace_llm_call(
        name="groq_generation",
        model="openai/gpt-oss-120b",
        input_prompt=prompt,
        metadata=metadata or {},
    ) as trace:
        start_time = time.time()
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": f"Tu dois répondre exclusivement en {nom_langue}. C'est une règle absolue et non négociable, peu importe la langue du contexte fourni."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=800
        )
        latency = time.time() - start_time
        
        # Extract token usage from Groq response
        usage = response.usage
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)
        total_tokens = getattr(usage, 'total_tokens', prompt_tokens + completion_tokens)
        
        # Groq free tier = coût 0
        estimated_cost = 0.0
        
        usage_stats = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency": latency,
            "estimated_cost": estimated_cost,
        }
        
        response_text = response.choices[0].message.content
        
        # Enregistrer dans Langfuse
        trace.set_output(response_text)
        trace.set_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            total_cost=estimated_cost,
        )
        trace.set_metadata(latency_seconds=latency)
        
        return response_text, usage_stats