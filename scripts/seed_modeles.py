from src.database.connection import SessionLocal
from src.database.models import Modele

def seed_modeles():
    db = SessionLocal()

    modeles = [
        # Modèles testés et fonctionnels avec les moyens actuels du stage (Groq, gratuit)
        Modele(nom="Llama 3.3 70B", fournisseur="Groq (Meta)", version="3.3", cout_par_1k_tokens=0.0),
        Modele(nom="Llama 3.1 8B Instant", fournisseur="Groq (Meta)", version="3.1", cout_par_1k_tokens=0.0),
        Modele(nom="Mixtral 8x7B", fournisseur="Groq (Mistral)", version="8x7B", cout_par_1k_tokens=0.0),
        Modele(nom="Gemma2 9B", fournisseur="Groq (Google)", version="9B", cout_par_1k_tokens=0.0),

        # Modèles cibles pour le benchmark final (nécessitent clés payantes, à obtenir via Ooredoo)
        Modele(nom="GPT-4o", fournisseur="OpenAI", version="2024-08", cout_par_1k_tokens=0.005),
        Modele(nom="GPT-4o-mini", fournisseur="OpenAI", version="2024-07", cout_par_1k_tokens=0.00015),
        Modele(nom="Claude 3.5 Sonnet", fournisseur="Anthropic", version="2024-10", cout_par_1k_tokens=0.003),
        Modele(nom="Gemini 1.5 Pro", fournisseur="Google", version="2024-09", cout_par_1k_tokens=0.0035),
    ]

    db.add_all(modeles)
    db.commit()
    db.close()
    print(f"{len(modeles)} modèles insérés avec succès.")

if __name__ == "__main__":
    seed_modeles()