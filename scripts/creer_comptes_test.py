import argparse
import secrets
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import hash_password


def generate_password() -> str:
    return secrets.token_urlsafe(10)


def create_test_users(apply: bool) -> None:
    users = [
        {"email": "client@ooredoo.com", "role": "client"},
        {"email": "admin@ooredoo.com", "role": "admin"},
        {"email": "superadmin@ooredoo.com", "role": "super_admin"},
    ]

    credentials = []
    with SessionLocal() as session:
        for user in users:
            password = generate_password()
            hashed = hash_password(password)
            credentials.append((user["email"], password, user["role"]))
            if apply:
                existing = session.scalars(select(Utilisateur).where(Utilisateur.email == user["email"]))
                if existing.first():
                    print(f"Compte déjà existant : {user['email']}")
                    continue
                utilisateur = Utilisateur(
                    email=user["email"],
                    mot_de_passe_hash=hashed,
                    role=user["role"],
                )
                session.add(utilisateur)
        if apply:
            session.commit()
            print("Comptes test insérés en base.")

    print("\nComptes de test générés :")
    for email, password, role in credentials:
        print(f"- {email} / {password} / role={role}")
    print("\nNote : ces mots de passe ne sont affichés qu'une seule fois.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Créer des comptes de test pour le dashboard.")
    parser.add_argument("--apply", action="store_true", help="Insérer les comptes en base")
    args = parser.parse_args()
    create_test_users(args.apply)
