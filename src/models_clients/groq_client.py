from groq import Groq
from langdetect import detect
from src.config.settings import GROQ_API_KEY

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


    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"Tu dois répondre exclusivement en {nom_langue}. C'est une règle absolue et non négociable, peu importe la langue du contexte fourni."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )

    return response.choices[0].message.content