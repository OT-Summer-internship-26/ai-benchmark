"""Ajoute Gemini 3.1 Flash-Lite dans la table modeles.

IMPORTANT : ce script laisse Postgres auto-assigner l'id (SERIAL), et
affiche l'id réellement attribué à la fin. Si ce n'est PAS 14, va corriger
"gemini-3.1-flash-lite": {"id": 14, ...} dans src/agents/executeur.py pour
que ça corresponde à l'id réel.

Usage :
    python scripts/ajouter_modele_gemini.py
"""

from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        # Évite le doublon si le script est relancé par erreur
        existing = conn.execute(
            text("SELECT id FROM modeles WHERE nom = :nom"),
            {"nom": "Gemini 3.1 Flash-Lite"}
        ).fetchone()

        if existing:
            print(f"Déjà présent en base avec id={existing[0]}. Rien à faire.")
            print(f"Vérifie que executeur.py utilise bien cet id pour 'gemini-3.1-flash-lite'.")
        else:
            result = conn.execute(
                text("""
                    INSERT INTO modeles (nom, fournisseur, version, cout_par_1k_tokens, date_ajout)
                    VALUES (:nom, :fournisseur, :version, :cout, NOW())
                    RETURNING id
                """),
                {
                    "nom": "Gemini 3.1 Flash-Lite",
                    "fournisseur": "Google",
                    "version": "3.1-flash-lite",
                    "cout": 0.0,  # gratuit dans les limites du free tier (rate-limited)
                }
            )
            nouvel_id = result.fetchone()[0]
            conn.commit()
            print(f"✅ Gemini 3.1 Flash-Lite ajouté avec id={nouvel_id}")

            if nouvel_id != 14:
                print(f"\n⚠️  ATTENTION : l'id attribué ({nouvel_id}) est différent de 14 !")
                print(f"   Va corriger MAPPING_MODELES dans src/agents/executeur.py :")
                print(f'   "gemini-3.1-flash-lite": {{"id": {nouvel_id}, "provider": "gemini"}},')