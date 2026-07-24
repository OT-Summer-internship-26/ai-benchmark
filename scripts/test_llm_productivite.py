from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    question = "Comment mettre en place une veille concurrentielle efficace ?"
    chunks = search_similar(question, "Productivité Personnelle", top_k=3)
    reponse = generate_response(question, chunks)
    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")