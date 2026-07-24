from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

if __name__ == "__main__":
    question = "Comment optimiser un article de blog pour le SEO ?"
    chunks = search_similar(question, "Marketing & Digital", top_k=3)
    reponse = generate_response(question, chunks)
    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")