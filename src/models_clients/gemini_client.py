from google import genai
from src.config.settings import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_response(question: str, context_chunks: list[str]) -> str:
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

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return response.text