from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    question = "How should I write an effective job description?"

    chunks = search_similar(question, "RH & Communication", top_k=3)
    reponse = generate_response(question, chunks)

    print(f"Question (anglais) : {question}\n")
    print(f"Réponse générée (doit être en anglais) :\n{reponse}")