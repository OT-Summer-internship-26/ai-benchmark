import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import hash_password

def reset_passwords():
    db = SessionLocal()
    passwords = {
        "client@ooredoo.com": "client123",
        "admin@ooredoo.com": "admin123",
        "superadmin@ooredoo.com": "superadmin123",
    }
    for email, pwd in passwords.items():
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if user:
            user.mot_de_passe_hash = hash_password(pwd)
            print(f"Updated {email} with password '{pwd}'")
        else:
            print(f"User {email} not found")
    db.commit()
    db.close()

if __name__ == "__main__":
    reset_passwords()
