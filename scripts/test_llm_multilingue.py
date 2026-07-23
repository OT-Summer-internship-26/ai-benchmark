from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    question = "How should I document an API for developers?"

    chunks = search_similar(question, "IT & Architecture", top_k=3)
    reponse = generate_response(question, chunks)

    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")