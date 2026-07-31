import requests
from langdetect import detect
from src.translation.translator import traduire_depuis_francais, detecter_arabe_tunisien

OLLAMA_URL = "http://localhost:11434/api/chat"

LANGUES_CIBLES = {
    "fr": "français",
    "en": "english",
    "ar": "العربية",
    "tn": "تونسية/دارجة",
}


def _detecter_langue(question: str) -> str:
    try:
        langue = detect(question)
        if langue == "ar" and detecter_arabe_tunisien(question):
            return "tn"
        return langue
    except Exception:
        return "fr"


def _build_prompt(question: str, context: str, langue: str) -> str:
    nom_langue = LANGUES_CIBLES.get(langue, LANGUES_CIBLES["fr"])
    return f"""Tu es un assistant professionnel pour Ooredoo.

RÈGLE OBLIGATOIRE : Réponds UNIQUEMENT dans la langue suivante : {nom_langue}.
Même si le contexte fourni est dans une autre langue, tu dois formuler ta réponse dans cette langue.

Question : {question}

Contexte :
{context}

INSTRUCTIONS :
1. Réponds directement, sans introduction ni préambule.
2. N'utilise jamais une autre langue que {nom_langue}.
3. Structure la réponse en points numérotés ou à puces si nécessaire.
4. Si l'information demandée n'est pas dans le contexte, dis-le clairement en une phrase courte.
5. Si la réponse nécessite un terme technique, garde-le dans la langue cible et évite les mélanges."""


def generate_response(question: str, context_chunks: list[str], model_name: str = "llama3.1:8b") -> str:
    context = "\n\n---\n\n".join(context_chunks)
    langue_de_la_question = _detecter_langue(question)

    prompt = _build_prompt(question, context, langue_de_la_question)

    response = requests.post(OLLAMA_URL, json={
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    })

    contenu_brouillon = response.json()["message"]["content"]

    if langue_de_la_question == "fr":
        return contenu_brouillon

    return traduire_depuis_francais(contenu_brouillon, langue_de_la_question)