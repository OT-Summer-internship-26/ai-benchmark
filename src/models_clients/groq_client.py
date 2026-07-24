from groq import Groq
from src.config.settings import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def generate_response(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""Tu es un assistant professionnel pour Ooredoo. Réponds à la question 
en te basant UNIQUEMENT sur le contexte fourni ci-dessous.

Contexte :
{context}

Question : {question}

INSTRUCTIONS FINALES CRITIQUES :
1. Identifie silencieusement la langue de la "Question" ci-dessus (français, anglais, 
arabe, espagnol, ou toute autre langue) et réponds ENTIÈREMENT dans cette même langue, 
même si le contexte est dans une autre langue.
2. Ne répète JAMAIS la question dans ta réponse.
3. Ne mentionne JAMAIS quelle langue tu as détectée ou utilisée (pas de phrase du type 
"la langue utilisée est..." ou "je vais répondre en...").
4. Va directement au contenu de la réponse, sans préambule ni méta-commentaire.
5. Si l'information n'est pas dans le contexte, dis-le brièvement puis donne les 
meilleurs éléments disponibles, sans t'excuser ni te justifier longuement."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )

    return response.choices[0].message.content