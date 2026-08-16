from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.utils.validation import validate_email, validate_password
from src.utils.exceptions import ValidationException, AuthenticationException
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rôles valides dans l'application, centralisés ici pour éviter de les
# redéfinir à plusieurs endroits (app.py, scripts de seed, etc.).
ROLES = ("client", "admin", "super_admin")


def hash_password(password: str) -> str:
    # Bcrypt has a 72-byte limit - truncate if necessary
    password_truncated = password[:72]
    return pwd_context.hash(password_truncated)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Bcrypt has a 72-byte limit - truncate if necessary
    password_truncated = plain_password[:72]
    return pwd_context.verify(password_truncated, hashed_password)


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def login(email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Vérifie les identifiants contre la base de données.

    Retourne :
        (utilisateur, None)      si la connexion réussit
        (None, message_erreur)   sinon

    L'utilisateur retourné est un simple dict {id, email, role} — jamais
    l'objet SQLAlchemy tel quel, pour ne pas garder de session ouverte une
    fois la valeur stockée dans st.session_state.

    Note : cette fonction ne vérifie PAS que le rôle correspond à un profil
    attendu (contrairement à do_login() dans app.py, qui ajoute cette
    vérification pour l'écran de login par profil). Elle sert de brique de
    base réutilisable ailleurs si besoin.
    """
    email = email.strip() if email else ""
    
    if not email or not password:
        msg = "Merci de renseigner un e-mail et un mot de passe."
        logger.warning(f"Login attempt with empty credentials")
        return None, msg

    if not validate_email(email):
        msg = "Format d'adresse e-mail invalide."
        logger.warning(f"Login attempt with invalid email format: {email}")
        return None, msg

    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()

        if user is None:
            msg = "Adresse e-mail introuvable."
            logger.warning(f"Login attempt with non-existent email: {email}")
            return None, msg

        if not verify_password(password, user.mot_de_passe_hash):
            msg = "Mot de passe incorrect."
            logger.warning(f"Failed login attempt for email: {email}")
            return None, msg

        logger.info(f"Successful login for user: {email}")
        return {"id": user.id, "email": user.email, "role": user.role}, None
    except Exception as e:
        msg = f"Database error during login: {str(e)}"
        logger.error(msg)
        return None, "Une erreur est survenue lors de la vérification des identifiants."
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Création de compte
# ---------------------------------------------------------------------------

def create_user(email: str, password: str, role: str = "client") -> tuple[bool, str]:
    """
    Crée un nouvel utilisateur après avoir vérifié :
      - que l'e-mail et le mot de passe sont renseignés
      - que le rôle demandé est valide (client / admin / super_admin)
      - que le mot de passe fait au moins 6 caractères
      - qu'aucun compte n'existe déjà avec cette adresse e-mail

    Retourne (True, message_succès) ou (False, message_erreur).
    """
    email = email.strip() if email else ""

    # Input validation
    if not email or not password:
        msg = "L'adresse e-mail et le mot de passe sont obligatoires."
        logger.warning(f"Create user attempt with empty fields")
        return False, msg
    
    if not validate_email(email):
        msg = "Format d'adresse e-mail invalide."
        logger.warning(f"Create user attempt with invalid email: {email}")
        return False, msg
    
    if role not in ROLES:
        msg = f"Rôle invalide. Rôles autorisés : {', '.join(ROLES)}."
        logger.warning(f"Create user attempt with invalid role: {role}")
        return False, msg
    
    is_valid, pwd_error = validate_password(password)
    if not is_valid:
        logger.warning(f"Create user attempt with weak password for: {email}")
        return False, pwd_error

    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if existing:
            msg = "Un compte existe déjà avec cette adresse e-mail."
            logger.warning(f"Create user attempt for existing email: {email}")
            return False, msg

        # Create new user
        user = Utilisateur(
            email=email,
            mot_de_passe_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        
        logger.info(f"User account created: email={email}, role={role}")
        return True, f"Compte créé pour {email} (rôle : {role})."

    except IntegrityError as e:
        # Race condition: user created between check and insert
        db.rollback()
        msg = "Un compte existe déjà avec cette adresse e-mail."
        logger.warning(f"Race condition on user creation for: {email}")
        return False, msg
    except Exception as e:
        # Unexpected error
        db.rollback()
        msg = "Erreur lors de la création du compte. Veuillez réessayer."
        logger.error(f"Unexpected error creating user: {str(e)}")
        return False, msg
    finally:
        db.close()
