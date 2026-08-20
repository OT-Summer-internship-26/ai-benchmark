from src.config.settings import GROQ_API_KEY
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)

r = client.chat.completions.create(
    model="qwen/qwen3.6-27b",
    messages=[
        {
            "role": "system",
            "content": 'Tu reponds UNIQUEMENT en JSON valide, sans texte autour, au format : {"note": <float entre 0 et 1>, "justification": "<une phrase courte>"}'
        },
        {
            "role": "user",
            "content": "Evalue cette reponse: Le poste requiert 3 ans experience Python. Contexte: Le candidat doit avoir 3 ans experience minimum en developpement Python."
        }
    ],
    max_tokens=1200,
    temperature=0,
)

print("--- finish_reason ---")
print(r.choices[0].finish_reason)
print("--- content brut (repr) ---")
print(repr(r.choices[0].message.content))
print("--- message complet ---")
print(r.choices[0].message)
print("--- usage (tokens) ---")
print(r.usage)