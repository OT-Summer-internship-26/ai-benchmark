from src.rag.vector_store import search_similar
from src.models_clients.groq_client import generate_response

print("="*70)
print("DEMO — RAG Ooredoo : Benchmark IA Adapté aux Besoins Métiers")
print("="*70)

demos = [
    ("RH & Communication", "Comment rédiger une fiche de poste efficace ?"),
    ("IT & Architecture", "Quelles sont les meilleures pratiques pour documenter une API ?"),
    ("Réseau / Support Technique (NOC)", "Quelles sont les étapes pour résoudre une panne de ligne dédiée ?"),
    ("Productivité Personnelle", "Comment mettre en place une veille concurrentielle efficace ?"),
    ("Marketing & Digital", "Comment optimiser un article de blog pour le SEO ?"),
]

for departement, question in demos:
    print(f"\n{'-'*70}")
    print(f"MÉTIER : {departement}")
    print(f"QUESTION : {question}")
    print(f"{'-'*70}")
    chunks = search_similar(question, departement, top_k=3)
    reponse = generate_response(question, chunks)
    print(f"\nRÉPONSE GÉNÉRÉE :\n{reponse}\n")

print("="*70)
print("FIN DE LA DEMO")
print("="*70)