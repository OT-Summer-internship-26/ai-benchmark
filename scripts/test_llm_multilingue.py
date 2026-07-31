from src.rag.vector_store import search_similar
from src.models_clients.ollama_client import generate_response

if __name__ == "__main__":
    
    question = "كيف يمكنني توثيق واجهة برمجة التطبيقات للمطورين؟"

    chunks = search_similar(question, "IT & Architecture", top_k=8)
    reponse = generate_response(question, chunks)

    print(f"Question : {question}\n")
    print(f"Réponse générée :\n{reponse}")

    with open("reponse_anglais.txt", "w", encoding="utf-8") as f:
        f.write(f"Question : {question}\n\n")
        f.write(f"Réponse générée :\n{reponse}")