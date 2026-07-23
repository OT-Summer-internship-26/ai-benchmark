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

INSTRUCTION FINALE CRITIQUE : Identifie la langue exacte utilisée dans la "Question" 
ci-dessus (peu importe la langue - français, anglais, arabe, espagnol, ou toute autre 
langue). Ta réponse doit être rédigée ENTIÈREMENT et UNIQUEMENT dans cette langue précise, 
même si ce prompt système est en français et même si le contexte est dans une autre langue. 
Ne mélange jamais les langues dans ta réponse."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )

    return response.choices[0].message.content