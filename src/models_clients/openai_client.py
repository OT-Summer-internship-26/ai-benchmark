from openai import OpenAI
from src.config.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_response(question: str, context_chunks: list[str]) -> str:
    """Génère une réponse LLM basée sur la question et les passages retrouvés par le RAG."""
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""Tu es un assistant professionnel pour Ooredoo. Réponds à la question 
en te basant UNIQUEMENT sur le contexte fourni ci-dessous.

IMPORTANT : Réponds TOUJOURS dans la même langue que la question posée, même si le 
contexte fourni est dans une langue différente. Si le contexte est en anglais et que 
la question est en français, traduis les informations pertinentes et réponds en français.

Si l'information n'est pas présente dans le contexte, dis-le clairement plutôt que 
d'inventer une réponse.

Contexte (peut être dans une langue différente de la question) :
{context}

Question : {question}

Réponse (dans la même langue que la question) :"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content