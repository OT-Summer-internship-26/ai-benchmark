import requests
from langdetect import detect
from src.translation.translator import traduire_depuis_francais, detecter_arabe_tunisien

OLLAMA_URL = "http://localhost:11434/api/chat"


def _detecter_langue(question: str) -> str:
    try:
        langue = detect(question)
        if langue == "ar" and detecter_arabe_tunisien(question):
            return "tn"
        return langue
    except Exception:
        return "fr"


def generate_response(question: str, context_chunks: list[str], model_name: str = "llama3.1:8b") -> str:
    context = "\n\n---\n\n".join(context_chunks)
    langue_de_la_question = _detecter_langue(question)

    # Le LLM genere TOUJOURS en francais
    # C'est une etape interne — NLLB s'occupe de la traduction apres
    prompt = f"""Tu es un assistant professionnel pour Ooredoo.
Reponds en FRANCAIS a la question suivante, en te basant UNIQUEMENT sur le contexte fourni.

Question : {question}

Contexte :
{context}

INSTRUCTIONS :
1. Reponds en francais uniquement.
2. Va directement au contenu, sans introduction ni preambule.
3. Ne repete JAMAIS la question dans ta reponse.
4. Structure la reponse en points numerotes ou a puces si necessaire.
5. Si l'information n'est pas dans le contexte, dis-le en une phrase courte."""

    response = requests.post(OLLAMA_URL, json={
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    })

    reponse_francaise = response.json()["message"]["content"]

    # Si la question est en francais, pas besoin de traduire
    if langue_de_la_question == "fr":
        return reponse_francaise

    # NLLB-200 traduit le francais vers la langue de la question
    return traduire_depuis_francais(reponse_francaise, langue_de_la_question)