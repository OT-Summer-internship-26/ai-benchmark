from src.database.connection import engine
from sqlalchemy import text

MODELES_OLLAMA = [
    ("Llama 3.1 8B (Ollama)", "Ollama (local)", "3.1", 0.0),
    ("Mistral 7B (Ollama)", "Ollama (local)", "7B", 0.0),
    ("Gemma2 9B (Ollama)", "Ollama (local)", "9B", 0.0),
    ("Qwen2.5 7B (Ollama)", "Ollama (local)", "7B", 0.0),
]

if __name__ == "__main__":
    with engine.connect() as conn:
        for nom, fournisseur, version, cout in MODELES_OLLAMA:
            conn.execute(
                text("""
                    INSERT INTO modeles (nom, fournisseur, version, cout_par_1k_tokens, date_ajout)
                    VALUES (:nom, :fournisseur, :version, :cout, NOW())
                """),
                {"nom": nom, "fournisseur": fournisseur, "version": version, "cout": cout}
            )
        conn.commit()
        print(f"{len(MODELES_OLLAMA)} modèles Ollama ajoutés.")