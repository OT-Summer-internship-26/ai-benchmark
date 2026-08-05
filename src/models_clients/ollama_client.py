import requests
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from src.translation.translator import traduire_depuis_francais, detecter_arabe_tunisien

OLLAMA_URL = "http://localhost:11434/api/chat"

LANGUES_SUPPORTEES = {"fr", "en", "ar", "tn"}
LANGUE_LABELS = {
    "fr": "français",
    "en": "English",
    "ar": "arabe",
    "tn": "tunisien",
}


def _detecter_langue(question: str) -> str:
    try:
        langue = detect(question)
        if langue == "ar" and detecter_arabe_tunisien(question):
            return "tn"
        return langue if langue in LANGUES_SUPPORTEES else "en"
    except (Exception, LangDetectException):
        return "fr"


def generate_response(question: str, context_chunks: list[str], model_name: str = "llama3.1:8b") -> str:
    context = "\n\n---\n\n".join(context_chunks)
    langue_de_la_question = _detecter_langue(question)
    label_langue = LANGUE_LABELS.get(langue_de_la_question, "anglais")

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

    response = requests.post(OLLAMA_URL, json={
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    })
    response.raise_for_status()

    content = response.json().get("message", {}).get("content")
    if content is None:
        raise ValueError("La réponse OLLAMA ne contient pas de contenu valide.")

    if langue_de_la_question == "fr":
        return content

    try:
        langue_reponse = detect(content)
    except (Exception, LangDetectException):
        langue_reponse = "fr"

    if langue_reponse == "fr" and langue_de_la_question in {"en", "ar", "tn"}:
        return traduire_depuis_francais(content, langue_de_la_question)

    return content
