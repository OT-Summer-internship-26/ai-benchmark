"""
Script de seed : crée les tables (si absentes) et insère un compte de
démonstration pour chacun des trois profils (client, admin, super_admin)
utilisés par l'écran de login du dashboard Streamlit.

Usage (depuis la racine du projet, Postgres démarré) :
    python scripts/seed_users.py
"""

import sys
from pathlib import Path

# Ajoute la racine du projet (le dossier qui contient "src") au chemin de
# recherche de Python. Nécessaire car lancer "python scripts/seed_users.py"
# ajoute seulement le dossier scripts/ au path, pas la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.connection import SessionLocal, engine
from src.database.models import Base, Utilisateur
from src.auth.utils import hash_password

# Adapte les emails/mots de passe si besoin — ce sont ceux déjà utilisés
# comme placeholders dans l'écran de login (DEMO_HINTS).
DEMO_USERS = [
    {"email": "client@ooredoo.com", "password": "client123", "role": "client"},
    {"email": "admin@ooredoo.com", "password": "admin123", "role": "admin"},
    {"email": "superadmin@ooredoo.com", "password": "superadmin123", "role": "super_admin"},
]


def main() -> None:
    # Crée toutes les tables définies dans src/database/models.py si elles
    # n'existent pas encore (ne touche pas aux tables déjà présentes).
    Base.metadata.create_all(bind=engine)
    print("Tables vérifiées / créées.")

    db = SessionLocal()
    try:
        for u in DEMO_USERS:
            existing = db.query(Utilisateur).filter(Utilisateur.email == u["email"]).first()
            if existing:
                print(f"  - déjà présent : {u['email']} ({u['role']})")
                continue

            user = Utilisateur(
                email=u["email"],
                mot_de_passe_hash=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)
            print(f"  - créé : {u['email']} / {u['password']} ({u['role']})")

        db.commit()
    finally:
        db.close()

    print("\nTerminé. Tu peux te connecter avec les identifiants ci-dessus sur l'écran de login.")


if __name__ == "__main__":
    main()