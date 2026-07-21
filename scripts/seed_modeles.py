from src.database.connection import SessionLocal
from src.database.models import Modele

def seed_modeles():
    db = SessionLocal()

    modeles = [
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