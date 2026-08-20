from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO modeles (nom, fournisseur, version, cout_par_1k_tokens, date_ajout)
                VALUES (:nom, :fournisseur, :version, :cout, NOW())
                RETURNING id
            """),
            {
                "nom": "Qwen3 8B (Ollama)",
                "fournisseur": "Ollama (local)",
                "version": "3",
                "cout": 0.0,
            }
        )
        new_id = result.fetchone()[0]
        conn.commit()
        print(f"✅ Qwen3 8B (Ollama) ajouté avec l'id = {new_id}")
        print("→ Note cet id : tu en auras besoin pour MAPPING_MODELES dans src/agents/executeur.py")