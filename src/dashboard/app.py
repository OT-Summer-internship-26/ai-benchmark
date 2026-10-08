import sys
import pathlib

# ---------------------------------------------------------------------------
# Path bootstrap — ensures `src` is importable regardless of which directory
# `streamlit run` is launched from.  Resolves to the project root:
#   ooredoo-ia-benchmark/
#       src/
#           dashboard/
#               app.py   ← this file  (__file__ is 2 levels below the root)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import pandas as pd
import io
import requests
import time
from sqlalchemy import text, bindparam
from sqlalchemy.exc import IntegrityError
from src.dashboard.logo import LOGO_B64

from src.database.connection import engine

from src.database.connection import SessionLocal
from src.database.models import Utilisateur, Scenario, Modele
from src.auth.utils import verify_password, hash_password
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__)

# Import centralized formatting utilities
from src.dashboard.formatting import (
    safe_format_score,
    safe_format_cost,
    safe_format_latency,
)
from src.dashboard.client_recommendation_page import render_client_recommendation_page


def format_executions_for_display(df, display_columns):
    """
    Format execution DataFrame for display, handling None values properly.
    """
    # Create a copy to avoid modifying the original
    display_df = df[display_columns].copy()
    
    # Format score columns (percentages)
    score_columns = ["score_global_auto", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for col in score_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: safe_format_score(x, as_percentage=True))
    
    # Format numeric columns
    if "latence_secondes" in display_df.columns:
        display_df["latence_secondes"] = display_df["latence_secondes"].apply(lambda x: safe_format_latency(x))
    
    if "cout_estime" in display_df.columns:
        display_df["cout_estime"] = display_df["cout_estime"].apply(lambda x: safe_format_cost(x))
    
    return display_df

# URL de base de l'API FastAPI (Sprint 3). Ajuste si elle tourne ailleurs
# (autre port, autre machine, etc.) — par exemple via une variable
# d'environnement si tu déploies un jour au-delà de ta machine locale.
API_BASE_URL = "http://127.0.0.1:8000"
# Nombre de scénarios attendu par département — utilisé pour le contrôle
# de complétude affiché dans l'onglet Administration.
SCENARIOS_CIBLE_PAR_DEPARTEMENT = 16


# ---------------------------------------------------------------------------
# Page config — called exactly ONCE, as the very first Streamlit command in
# the whole script (unconditionally). This avoids the classic Streamlit
# error "set_page_config() can only be called once" that happens when it's
# called separately inside both the login screen and the main app.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Benchmark IA — Ooredoo",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Helpers pédagogiques pour les graphiques (ajout)
# ---------------------------------------------------------------------------

def score_to_label(score) -> str:
    """Convertit un score brut (0-1) en label qualitatif compréhensible
    pour un public non-technique (utilisé côté Client)."""
    if score is None or pd.isna(score):
        return "N/A"
    if score >= 0.75:
        return "🟢 Excellent"
    if score >= 0.5:
        return "🟡 Correct"
    return "🔴 À améliorer"


@st.cache_data
def load_executions(limit: int | None = 200) -> pd.DataFrame:
    """Load execution data with comprehensive error handling."""
    logger.debug(f"Loading executions with limit: {limit}")
    
    try:
        limit_clause = "LIMIT :limit" if limit is not None else ""
        with engine.connect() as conn:
            executions = pd.read_sql(
                text(
                    f"""
                    SELECT
                        e.id AS execution_id,
                        e.scenario_id,
                        s.nom_cas_usage,
                        s.departement,
                        m.id AS modele_id,
                        m.nom AS modele_nom,
                        e.reponse_generee,
                        e.latence_secondes,
                        e.cout_estime,
                        e.date_execution
                    FROM executions e
                    JOIN scenarios s ON s.id = e.scenario_id
                    JOIN modeles m ON m.id = e.modele_id
                    WHERE e.id IN (
                        SELECT DISTINCT sc.execution_id FROM scores sc
                        WHERE sc.methode = 'ragas'
                          AND COALESCE(sc.is_legacy, FALSE) = FALSE
                          AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                          AND sc.note BETWEEN 0 AND 1
                    )
                    ORDER BY e.date_execution DESC
                    {limit_clause}
                    """
                ),
                conn,
                params={"limit": limit} if limit is not None else {},
            )

            if executions.empty:
                logger.warning("No executions found in database")
                return executions

            # Fetch only RAGAS criteria (0.0-1.0) to avoid mixing legacy heuristics.
            # NOTE: "IN :ids" needs an expanding bindparam with SQLAlchemy, otherwise
            # it can fail (or silently misbehave) depending on the DBAPI/driver.
            execution_ids = executions["execution_id"].tolist()
            if not execution_ids:
                logger.warning("No execution IDs found for score loading")
                executions["score_global_auto"] = None
                executions["score_global_display"] = None
                return executions
                
            scores_query = text(
                "SELECT execution_id, critere, note, commentaire "
                "FROM scores WHERE execution_id IN :ids "
                "AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') "
                "AND methode = 'ragas' "
                "AND COALESCE(is_legacy, FALSE) = FALSE "
                "AND note BETWEEN 0 AND 1"
            ).bindparams(bindparam("ids", expanding=True))

            scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})

        if scores.empty:
            logger.info("No scores found for executions, returning executions without scores")
            executions["score_global_auto"] = None
            executions["score_global_display"] = None
            return executions

        pivot_scores = scores.pivot_table(
            index="execution_id",
            columns="critere",
            values="note",
            aggfunc="first",
        ).reset_index()

        pivot_comments = scores.pivot_table(
            index="execution_id",
            columns="critere",
            values="commentaire",
            aggfunc="first",
        ).reset_index()
        pivot_comments = pivot_comments.rename(
            columns={
                "faithfulness": "faithfulness_comment",
                "answer_relevancy": "answer_relevancy_comment",
                "context_precision": "context_precision_comment",
                "context_recall": "context_recall_comment",
                "score_global": "score_global_comment",
            }
        )

        df = executions.merge(pivot_scores, on="execution_id", how="left")
        df = df.merge(pivot_comments, on="execution_id", how="left")
        
        # Ensure score columns exist and are numeric (coercing None/invalid to NaN so skipna works cleanly)
        score_columns = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        for col in score_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = None
        
        # Calculate global score only from available (non-None/non-NaN) values
        # For non-RAG scenarios where faithfulness, precision, recall are N/A,
        # global score is based purely on answer_relevancy (or available criteria).
        df["score_global_auto"] = (
            df[score_columns]
            .mean(axis=1, skipna=True)  # skipna=True ignores N/A metrics
            .round(3)
        )
        # If all criteria are NaN, mean produces NaN; keep as None for consistency
        df["score_global_auto"] = df["score_global_auto"].where(df["score_global_auto"].notna(), None)
        df["score_global_display"] = df["score_global_auto"]
        
        logger.info(f"Successfully loaded {len(df)} executions with scores")
        return df
        
    except Exception as e:
        logger.error(f"Error loading executions: {e}", exc_info=True)
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            "execution_id", "scenario_id", "nom_cas_usage", "departement", 
            "modele_id", "modele_nom", "reponse_generee", "latence_secondes", 
            "cout_estime", "date_execution", "score_global_auto", "score_global_display"
        ])



@st.cache_data
def load_scenario_catalog() -> pd.DataFrame:
    """Charge tous les scénarios existants (avec ou sans exécutions), triés par département."""
    logger.debug("Loading scenario catalog")
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text("SELECT departement, nom_cas_usage FROM scenarios ORDER BY departement, nom_cas_usage"),
                conn,
            )
        
        logger.info(f"Successfully loaded {len(df)} scenarios from catalog")
        return df
        
    except Exception as e:
        logger.error(f"Error loading scenario catalog: {e}", exc_info=True)
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=["departement", "nom_cas_usage"])

def format_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "date_execution" in df.columns:
        df["date_execution"] = pd.to_datetime(df["date_execution"])
    return df


def build_metric_cards(df: pd.DataFrame, client_mode: bool = False, total_executions_in_db: int | None = None) -> None:
    """Affiche les 4 cartes de métriques clés.
    Indique clairement si les exécutions affichées représentent un sous-ensemble filtré/limité.
    """
    col1, col2, col3, col4 = st.columns(4)
    nb_exec = len(df)
    if total_executions_in_db and total_executions_in_db > nb_exec:
        col1.metric("Exécutions", f"{nb_exec} / {total_executions_in_db}")
    else:
        col1.metric("Exécutions", nb_exec)
    col2.metric("Modèles", df["modele_nom"].nunique() if not df.empty else 0)
    col3.metric("Scénarios", df["nom_cas_usage"].nunique() if not df.empty else 0)
    if "score_global_auto" in df.columns:
        moyenne = df["score_global_auto"].mean()
        if client_mode:
            col4.metric("Qualité globale", score_to_label(moyenne))
        else:
            col4.metric("Score global moyen", f"{round(moyenne, 3):.3f}" if pd.notna(moyenne) else "N/A")
    else:
        col4.metric("Qualité globale" if client_mode else "Score global moyen", "N/A")


def build_client_department_comparison(filtered: pd.DataFrame) -> None:
    """Vue orientée décision métier : pour chaque département, quel est
    le modèle le plus performant ? Remplace la table technique de modèles
    dans l'interface Client."""
    st.markdown("## Quel modèle IA pour quel besoin ?")
    st.write(
        "Cette vue vous aide à choisir le modèle IA le plus adapté selon le "
        "département ou le type de besoin métier."
    )

    if "departement" not in filtered.columns or filtered.empty:
        st.info("Pas assez de données pour établir une recommandation par département.")
        return

    dept_summary = (
        filtered.dropna(subset=["score_global_auto"])
        .groupby(["departement", "modele_nom"])["score_global_auto"]
        .mean()
        .reset_index()
    )

    if dept_summary.empty:
        st.info("Pas assez de données pour établir une recommandation par département.")
        return

    best_per_dept = (
        dept_summary.sort_values("score_global_auto", ascending=False)
        .groupby("departement")
        .first()
        .reset_index()
    )
    best_per_dept["Recommandation"] = best_per_dept["score_global_auto"].apply(score_to_label)

    st.table(
        best_per_dept.rename(columns={
            "departement": "Département",
            "modele_nom": "Modèle recommandé",
        })[["Département", "Modèle recommandé", "Recommandation"]]
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

ROLE_DISPLAY = {
    "client": "Utilisateur",
    "admin": "Administrateur",
    "super_admin": "Super Admin",
}

ROLE_OPTIONS = list(ROLE_DISPLAY.keys())


def do_login(email: str, password: str) -> bool:
    """
    Vérifie les identifiants en base. Retourne True en cas de succès.
    Le rôle est lu directement depuis utilisateurs.role après bcrypt verification.
    """
    logger.info(f"Login attempt for email: {email}")
    
    # Clear any existing login error
    st.session_state["login_error"] = None
    
    # Input validation
    email = email.strip() if email else ""
    password = password.strip() if password else ""
    
    if not email or not password:
        error_msg = "Merci de renseigner un e-mail et un mot de passe."
        logger.warning(f"Login failed - empty credentials: {error_msg}")
        st.session_state["login_error"] = error_msg
        return False
    
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        logger.debug(f"Database query completed - user found: {user is not None}")
        
        if user is None:
            error_msg = "Adresse e-mail introuvable."
            logger.warning(f"Login failed - user not found: {email}")
            st.session_state["login_error"] = error_msg
            return False
        
        if not verify_password(password, user.mot_de_passe_hash):
            error_msg = "Mot de passe incorrect."
            logger.warning(f"Login failed - incorrect password for user: {email}")
            st.session_state["login_error"] = error_msg
            return False

        # Login successful - set session state with role from database
        st.session_state["login_error"] = None
        st.session_state["auth_email"] = user.email
        st.session_state["auth_role"] = ROLE_DISPLAY.get(user.role, user.role)
        st.session_state["auth_role_key"] = user.role  # Store DB role key for checks
        st.session_state["auth_user_id"] = user.id
        st.session_state["auth_department"] = user.departement
        
        logger.info(f"Login successful for user: {email} with role: {user.role}")

        # Try to get API token (optional - don't fail login if this fails)
        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": email, "password": password},
                timeout=60,
            )
            resp.raise_for_status()
            st.session_state["api_token"] = resp.json()["token"]
            st.session_state["api_token_error"] = None
            logger.debug("API token obtained successfully")
        except Exception as e:
            st.session_state["api_token"] = None  # pilotage indisponible si l'API est down
            st.session_state["api_token_error"] = str(e)
            logger.warning(f"Failed to obtain API token: {e}")

        return True
        
    except Exception as e:
        error_msg = f"Erreur lors de la vérification des identifiants: {str(e)}"
        logger.error(f"Database error during login: {e}", exc_info=True)
        st.session_state["login_error"] = "Une erreur technique est survenue. Veuillez réessayer."
        return False
    finally:
        db.close()
    





def change_password_form():
    """Form for logged-in users to change their password."""
    st.subheader("Changer mon mot de passe")
    
    with st.form("change_password_form"):
        old_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submitted = st.form_submit_button("Modifier le mot de passe")
    
    if submitted:
        email = st.session_state.get("auth_email")
        
        if not old_password or not new_password or not confirm_password:
            st.error("Tous les champs sont obligatoires.")
            return
        
        if new_password != confirm_password:
            st.error("Les nouveaux mots de passe ne correspondent pas.")
            return
        
        # Validate new password
        from src.utils.validation import validate_password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            st.error(error_msg)
            return
        
        db = SessionLocal()
        try:
            user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
            
            if not user:
                st.error("Utilisateur introuvable.")
                return
            
            # Verify old password
            if not verify_password(old_password, user.mot_de_passe_hash):
                st.error("Mot de passe actuel incorrect.")
                return
            
            # Update password
            user.mot_de_passe_hash = hash_password(new_password)
            db.commit()
            
            st.success("✅ Mot de passe modifié avec succès !")
            logger.info(f"Password changed for user: {email}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error changing password: {e}")
            st.error("Une erreur est survenue lors de la modification du mot de passe.")
        finally:
            db.close()


def admin_reset_user_password(user_email: str, new_password: str) -> tuple[bool, str]:
    """Super admin function to reset any user's password (without requiring old password)."""
    from src.utils.validation import validate_password
    
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return False, error_msg
    
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == user_email).first()
        
        if not user:
            return False, "Utilisateur introuvable."
        
        user.mot_de_passe_hash = hash_password(new_password)
        db.commit()
        
        logger.info(f"Password reset by admin for user: {user_email}")
        return True, "Mot de passe réinitialisé avec succès."
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting password: {e}")
        return False, "Erreur lors de la réinitialisation du mot de passe."
    finally:
        db.close()


def do_signup(email: str, nom_complet: str, departement: str, password: str, confirm_password: str) -> bool:
    """
    Crée un nouveau compte client (role='client', is_approved=FALSE).
    L'utilisateur doit attendre l'approbation d'un admin avant de se connecter.
    Pas de connexion automatique.
    """
    email = email.strip()
    nom_complet = nom_complet.strip() if nom_complet else ""

    if not email or not password:
        st.session_state["login_error"] = "Merci de remplir tous les champs."
        return False
    
    if not nom_complet:
        st.session_state["login_error"] = "Le nom complet est obligatoire."
        return False
    
    if not departement:
        st.session_state["login_error"] = "Veuillez sélectionner un département."
        return False
        
    if password != confirm_password:
        st.session_state["login_error"] = "Les mots de passe ne correspondent pas."
        return False
    if len(password) < 6:
        st.session_state["login_error"] = "Le mot de passe doit contenir au moins 6 caractères."
        return False

    db = SessionLocal()
    try:
        existing = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if existing:
            st.session_state["login_error"] = "Un compte existe déjà avec cette adresse e-mail."
            return False

        user = Utilisateur(
            email=email,
            nom_complet=nom_complet,
            departement=departement,
            mot_de_passe_hash=hash_password(password),
            role="client",
            is_approved=False,  # Awaiting approval
        )
        db.add(user)
        db.commit()
        
        st.session_state["login_error"] = None
        st.session_state["signup_success"] = (
            "Votre demande d'accès a été soumise. "
            "Un administrateur doit valider votre compte avant votre première connexion."
        )
        logger.info(f"New signup pending approval: {email} (dept: {departement})")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Signup error: {e}")
        st.session_state["login_error"] = "Erreur lors de la création du compte."
        return False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Gestion des utilisateurs (réservée au super admin, une fois connecté)
# ---------------------------------------------------------------------------

def admin_list_users():
    """Retourne tous les comptes, triés par rôle puis par email."""
    db = SessionLocal()
    try:
        return (
            db.query(Utilisateur)
            .order_by(Utilisateur.role, Utilisateur.email)
            .all()
        )
    finally:
        db.close()


def admin_list_pending_approvals():
    """Retourne les comptes clients en attente d'approbation."""
    db = SessionLocal()
    try:
        return (
            db.query(Utilisateur)
            .filter(Utilisateur.role == "client", Utilisateur.is_approved == False)
            .order_by(Utilisateur.date_creation.desc())
            .all()
        )
    finally:
        db.close()


def admin_approve_user(user_id: int, final_departement: str) -> tuple[bool, str]:
    """Approuve un compte client et assigne le département final."""
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if not user:
            return False, "Utilisateur introuvable."
        
        user.is_approved = True
        user.departement = final_departement
        db.commit()
        
        logger.info(f"User approved: {user.email} (dept: {final_departement})")
        return True, f"Compte {user.email} approuvé avec succès."
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving user: {e}")
        return False, "Erreur lors de l'approbation."
    finally:
        db.close()


def admin_reject_user(user_id: int) -> tuple[bool, str]:
    """Refuse et supprime un compte en attente d'approbation."""
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if not user:
            return False, "Utilisateur introuvable."
        
        email = user.email
        db.delete(user)
        db.commit()
        
        logger.info(f"User rejected and deleted: {email}")
        return True, f"Compte {email} refusé et supprimé."
    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting user: {e}")
        return False, "Erreur lors du refus."
    finally:
        db.close()


def admin_create_user(email: str, password: str, role: str) -> tuple[bool, str]:
    """Crée un compte avec le rôle de son choix. Ne connecte personne :
    réservé à un super admin qui provisionne un compte pour quelqu'un d'autre."""
    email = email.strip()

    if not email or not password:
        return False, "Merci de remplir tous les champs."
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if role not in ROLE_OPTIONS:
        return False, "Rôle invalide."

    db = SessionLocal()
    try:
        if db.query(Utilisateur).filter(Utilisateur.email == email).first():
            return False, "Un compte existe déjà avec cette adresse e-mail."
        db.add(
            Utilisateur(
                email=email,
                mot_de_passe_hash=hash_password(password),
                role=role,
            )
        )
        db.commit()
        return True, f"Compte créé pour {email} ({ROLE_DISPLAY.get(role, role)})."
    finally:
        db.close()


def admin_update_role(user_id: int, new_role: str) -> tuple[bool, str]:
    if new_role not in ROLE_OPTIONS:
        return False, "Rôle invalide."
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if user is None:
            return False, "Compte introuvable."
        user.role = new_role
        db.commit()
        return True, f"Rôle mis à jour : {user.email} → {ROLE_DISPLAY.get(new_role, new_role)}."
    finally:
        db.close()


def admin_reset_password(user_id: int, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if user is None:
            return False, "Compte introuvable."
        user.mot_de_passe_hash = hash_password(new_password)
        db.commit()
        return True, f"Mot de passe réinitialisé pour {user.email}."
    finally:
        db.close()


def admin_delete_user(user_id: int, requester_email: str) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.id == user_id).first()
        if user is None:
            return False, "Compte introuvable."
        if user.email == requester_email:
            return False, "Impossible de supprimer votre propre compte pendant que vous êtes connecté avec."
        db.delete(user)
        db.commit()
        return True, f"Compte {user.email} supprimé."
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pilotage du benchmark (réservé à Admin + Super Admin)
# ---------------------------------------------------------------------------

DEPARTEMENTS_OFFICIELS = [
    "RH",
    "Marketing & Digital",
    "IT & Cybersécurité",
    "Productivité & Transversal",
    "Service Client",
]

DEPARTEMENTS_MAPPING = {
    "RH": "RH",
    "RH & Communication": "RH",
    "Ressources Humaines": "RH",
    "Marketing": "Marketing & Digital",
    "Marketing & Digital": "Marketing & Digital",
    "IT": "IT & Cybersécurité",
    "IT & Architecture": "IT & Cybersécurité",
    "IT & Cybersécurité": "IT & Cybersécurité",
    "Réseau / Support Technique (NOC)": "IT & Cybersécurité",
    "Productivité": "Productivité & Transversal",
    "Productivité Personnelle": "Productivité & Transversal",
    "Productivité & Transversal": "Productivité & Transversal",
    "Service Client": "Service Client",
}

MODELES_DISPONIBLES = [
    "llama3.1:8b",
    "mistral:7b",
    "qwen3:8b",
    "qwen2.5:7b",
    "gemma2:9b",
    "gemini-3.1-flash-lite",
]


def _execute_benchmark_direct(scenario_ids: list[int], model_names: list[str]) -> tuple[bool, dict | str]:
    """Exécution directe du pipeline LangGraph sans dépendance externe à l'API."""
    try:
        from src.agents.graph import benchmark_graph
        config_initial = {
            "scenario_ids": scenario_ids,
            "model_names": model_names,
            "scenarios": [],
            "executions": [],
            "scores": [],
            "rapport": None,
            "erreurs": [],
        }
        resultat = benchmark_graph.invoke(config_initial)
        executions = resultat.get("executions", [])
        scenarios = resultat.get("scenarios", [])
        erreurs = resultat.get("erreurs", [])
        return True, {
            "status": "completed" if not erreurs else "completed_with_errors",
            "nb_scenarios": len(scenarios),
            "nb_models": len(model_names),
            "nb_executions": len(executions),
            "rapport": resultat.get("rapport"),
            "erreurs": erreurs,
            "initiated_by": "direct_execution",
        }
    except Exception as exc:
        logger.error(f"Direct benchmark execution failed: {exc}")
        return False, f"Erreur lors de l'exécution du benchmark : {exc}"


def trigger_benchmark_run(
    scenario_ids: list[int] | None,
    model_names: list[str] | None,
    timeout: int = 900,
) -> tuple[bool, dict | str]:
    if not scenario_ids or not model_names:
        return False, "Veuillez sélectionner au moins un scénario et un modèle."

    payload = {
        "scenario_ids": scenario_ids,
        "model_names": model_names,
    }
    token = st.session_state.get("api_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Tentative via l'API FastAPI si disponible
    if token:
        try:
            response = requests.post(
                f"{API_BASE_URL}/benchmark/run", json=payload, headers=headers, timeout=timeout
            )
            if response.status_code == 200:
                return True, response.json()
            logger.warning(f"API /benchmark/run code {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Appel API échoué ({e}) — bascule sur exécution directe du pipeline.")

    # Exécution directe si API indisponible ou sans token valide
    return _execute_benchmark_direct(scenario_ids, model_names)


# --- Catalogue des scénarios -----------------------------------------------

def admin_list_scenarios():
    db = SessionLocal()
    try:
        return (
            db.query(Scenario)
            .order_by(Scenario.departement, Scenario.nom_cas_usage)
            .all()
        )
    finally:
        db.close()


def admin_scenarios_completeness() -> pd.DataFrame:
    """Affiche la complétude du catalogue de scénarios strictement pour les
    5 départements officiels, sans colonne Statut."""
    scenarios = admin_list_scenarios()
    
    counts: dict[str, int] = {dep: 0 for dep in DEPARTEMENTS_OFFICIELS}
    for s in scenarios:
        official_dept = DEPARTEMENTS_MAPPING.get(s.departement, s.departement)
        if official_dept in counts:
            counts[official_dept] += 1
        else:
            counts[official_dept] = counts.get(official_dept, 0) + 1

    rows = [{"Département": dep, "Nb scénarios": counts.get(dep, 0)} for dep in DEPARTEMENTS_OFFICIELS]
    return pd.DataFrame(rows)


def admin_create_scenario(
    departement: str, metier: str, nom_cas_usage: str,
    prompt: str, sortie_attendue: str, critere_succes: str,
) -> tuple[bool, str]:
    departement = departement.strip()
    nom_cas_usage = nom_cas_usage.strip()
    prompt = prompt.strip()

    if not departement or not nom_cas_usage or not prompt:
        return False, "Département, nom du cas d'usage et prompt sont obligatoires."

    db = SessionLocal()
    try:
        db.add(
            Scenario(
                departement=departement,
                metier=metier.strip() or None,
                nom_cas_usage=nom_cas_usage,
                prompt=prompt,
                sortie_attendue=sortie_attendue.strip() or None,
                critere_succes=critere_succes.strip() or None,
            )
        )
        db.commit()
        return True, f"Scénario « {nom_cas_usage} » créé."
    finally:
        db.close()


def admin_update_scenario(
    scenario_id: int, departement: str, metier: str, nom_cas_usage: str,
    prompt: str, sortie_attendue: str, critere_succes: str,
) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario is None:
            return False, "Scénario introuvable."

        scenario.departement = departement.strip()
        scenario.metier = metier.strip() or None
        scenario.nom_cas_usage = nom_cas_usage.strip()
        scenario.prompt = prompt.strip()
        scenario.sortie_attendue = sortie_attendue.strip() or None
        scenario.critere_succes = critere_succes.strip() or None
        db.commit()
        return True, f"Scénario « {scenario.nom_cas_usage} » mis à jour."
    finally:
        db.close()


def admin_delete_scenario(scenario_id: int) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario is None:
            return False, "Scénario introuvable."
        db.delete(scenario)
        db.commit()
        return True, "Scénario supprimé."
    except IntegrityError:
        db.rollback()
        return False, "Impossible de supprimer : des exécutions existent encore pour ce scénario."
    finally:
        db.close()


# --- Catalogue des modèles ---------------------------------------------------

def admin_list_models():
    db = SessionLocal()
    try:
        return db.query(Modele).order_by(Modele.nom).all()
    finally:
        db.close()


def admin_create_model(
    nom: str, fournisseur: str, version: str, cout_par_1k_tokens: float | None,
) -> tuple[bool, str]:
    nom = nom.strip()
    if not nom:
        return False, "Le nom du modèle est obligatoire."

    db = SessionLocal()
    try:
        if db.query(Modele).filter(Modele.nom == nom).first():
            return False, "Un modèle avec ce nom existe déjà."
        db.add(
            Modele(
                nom=nom,
                fournisseur=fournisseur.strip() or None,
                version=version.strip() or None,
                cout_par_1k_tokens=cout_par_1k_tokens,
            )
        )
        db.commit()
        return True, f"Modèle « {nom} » ajouté au catalogue."
    finally:
        db.close()


def admin_update_model(
    model_id: int, nom: str, fournisseur: str, version: str, cout_par_1k_tokens: float | None,
) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        modele = db.query(Modele).filter(Modele.id == model_id).first()
        if modele is None:
            return False, "Modèle introuvable."
        modele.nom = nom.strip()
        modele.fournisseur = fournisseur.strip() or None
        modele.version = version.strip() or None
        modele.cout_par_1k_tokens = cout_par_1k_tokens
        db.commit()
        return True, f"Modèle « {modele.nom} » mis à jour."
    finally:
        db.close()


def admin_delete_model(model_id: int) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        modele = db.query(Modele).filter(Modele.id == model_id).first()
        if modele is None:
            return False, "Modèle introuvable."
        db.delete(modele)
        db.commit()
        return True, "Modèle supprimé du catalogue."
    except IntegrityError:
        db.rollback()
        return False, "Impossible de supprimer : des exécutions existent encore pour ce modèle."
    finally:
        db.close()


def _inject_login_css() -> None:
    """CSS pour page de login PLEIN ÉCRAN."""
    # Charger les logos TRANSPARENTS depuis assets (PAS de LOGO_B64)
    from src.dashboard.login_assets import get_wordmark_white_base64, get_emblem_base64
    
    wordmark_b64 = get_wordmark_white_base64()
    emblem_b64 = get_emblem_base64()
    
    st.markdown(
        f"""
        <style>
        /* Masquer header/footer/sidebar */
        header {{visibility:hidden;}}
        #MainMenu {{visibility:hidden;}}
        footer {{visibility:hidden;}}
        section[data-testid="stSidebar"] {{ display: none !important; }}

        /* Fond plein écran - BLANC (même couleur que la carte) */
        div[data-testid="stAppViewContainer"] {{
            background: #FFFFFF;
            background-attachment: fixed;
        }}
        
        div[data-testid="stMain"] {{ 
            display: flex; 
        }}
        
        /* Container PLEIN ÉCRAN - padding 0 */
        div.block-container {{
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }}

        /* Carte login PLEIN ÉCRAN 100vw x 100vh */
        .st-key-login_card {{
            width: 100vw;
            min-height: 100vh;
            margin: 0;
            background: white;
            border-radius: 0;
            box-shadow: none;
            overflow: hidden;
            display: flex;
        }}
        
        /* Gap 0 entre les colonnes */
        .st-key-login_card > div[data-testid="column"] {{
            padding: 0 !important;
            gap: 0 !important;
        }}
        
        .st-key-login_card > div {{
            gap: 0 !important;
        }}
        
        /* Panneau GAUCHE - Branding Ooredoo PLEIN ÉCRAN */
        .st-key-login_left {{
            background: linear-gradient(165deg, #ED1C24 0%, #B30006 100%);
            padding: 80px 60px;
            position: relative;
            overflow: hidden;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        
        /* Bulles décoratives - grande sphère blanche top-right */
        .st-key-login_left::before {{
            content: "";
            position: absolute;
            width: 420px;
            height: 420px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.20) 0%, rgba(255,255,255,0.08) 50%, transparent 75%);
            top: -180px;
            right: -150px;
            pointer-events: none;
            z-index: 1;
        }}
        
        /* Bulle rouge foncé bottom-left */
        .st-key-login_left::after {{
            content: "";
            position: absolute;
            width: 350px;
            height: 350px;
            border-radius: 50%;
            background: radial-gradient(circle at 40% 40%, rgba(179,0,6,0.6) 0%, rgba(139,0,5,0.4) 60%, transparent 80%);
            bottom: -120px;
            left: -100px;
            pointer-events: none;
            z-index: 1;
        }}
        
        /* Contenu du panneau gauche */
        .login-left-content {{
            position: relative;
            z-index: 2;
            text-align: center;
            max-width: 500px;
        }}
        
        /* Logo Ooredoo officiel */
        .login-left-content .wordmark {{
            max-width: 280px;
            width: 100%;
            height: auto;
            margin-bottom: 50px;
            display: block;
            margin-left: auto;
            margin-right: auto;
        }}
        
        /* Titre principal */
        .login-left-content .brand-title {{
            color: white;
            font-size: 44px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 24px;
            letter-spacing: -0.5px;
        }}
        
        /* Sous-titre */
        .login-left-content .brand-subtitle {{
            color: rgba(255,255,255,0.90);
            font-size: 18px;
            line-height: 1.6;
            font-weight: 400;
        }}
        
        /* Panneau DROIT - Formulaire PLEIN ÉCRAN */
        .st-key-login_right {{
            padding: 80px 60px;
            background: #FFFFFF;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }}
        
        /* Conteneur du formulaire */
        .login-form-container {{
            max-width: 420px;
            width: 100%;
        }}
        
        .st-key-login_right h2 {{
            color: #1a1a1a;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .st-key-login_right .form-subtitle {{
            color: #6B7280;
            font-size: 15px;
            margin-bottom: 36px;
        }}
        
        /* Inputs du formulaire - bordures arrondies propres */
        .st-key-login_right input {{
            background: #F3F4F7 !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            font-size: 15px !important;
            transition: all 0.2s ease;
        }}
        
        .st-key-login_right input:focus {{
            border-color: #ED1C24 !important;
            box-shadow: 0 0 0 3px rgba(237,28,36,0.08) !important;
            background: #FFFFFF !important;
        }}
        
        .st-key-login_right label {{
            font-weight: 500 !important;
            color: #374151 !important;
            font-size: 14px !important;
        }}
        
        /* Bouton submit ROUGE */
        .st-key-login_right div[data-testid="stFormSubmitButton"] button,
        .st-key-login_right button[kind="primary"] {{
            background: #ED1C24 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 16px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            width: 100%;
            transition: background 0.2s ease, transform 0.1s ease;
            margin-top: 8px;
        }}
        
        .st-key-login_right div[data-testid="stFormSubmitButton"] button:hover,
        .st-key-login_right button[kind="primary"]:hover {{
            background: #B30006 !important;
            transform: translateY(-1px);
        }}
        
        .st-key-login_right div[data-testid="stFormSubmitButton"] button:active {{
            transform: translateY(0);
        }}
        
        /* Liens sous le formulaire */
        .form-links {{
            margin-top: 24px;
            text-align: center;
            display: flex;
            justify-content: space-between;
            gap: 12px;
        }}
        
        .form-links button {{
            color: #ED1C24 !important;
            background: transparent !important;
            border: none !important;
            text-decoration: none;
            font-size: 14px !important;
            padding: 8px 4px !important;
            font-weight: 500 !important;
            transition: opacity 0.2s ease;
        }}
        
        .form-links button:hover {{
            opacity: 0.8;
            text-decoration: underline;
        }}
        
        /* Bouton retour */
        .back-button {{
            margin-top: 20px;
        }}
        
        .back-button button {{
            color: #6B7280 !important;
            background: transparent !important;
            border: none !important;
            font-size: 14px !important;
            padding: 8px 4px !important;
        }}
        
        /* Selectbox département */
        .st-key-login_right div[data-baseweb="select"] {{
            background: #F3F4F7 !important;
            border-radius: 12px !important;
            border: 1px solid #E5E7EB !important;
        }}
        
        /* Responsive - Mobile */
        @media (max-width: 900px) {{
            .st-key-login_card {{
                flex-direction: column;
            }}
            
            .st-key-login_left {{
                min-height: 40vh;
                padding: 50px 30px;
            }}
            
            .login-left-content .wordmark {{
                width: 200px;
                margin-bottom: 30px;
            }}
            
            .login-left-content .brand-title {{
                font-size: 32px;
            }}
            
            .login-left-content .brand-subtitle {{
                font-size: 16px;
            }}
            
            /* Atténuer les bulles sur mobile */
            .st-key-login_left::before {{
                opacity: 0.5;
            }}
            
            .st-key-login_left::after {{
                opacity: 0.5;
            }}
            
            .emblem-bubble {{
                width: 120px;
                height: 120px;
                bottom: 30px;
                right: 30px;
            }}
            
            .emblem-bubble img {{
                width: 60px;
            }}
            
            .st-key-login_right {{
                padding: 50px 30px;
                min-height: 60vh;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def login_page():
    """Page de login plein écran avec carte scindée - role déterminé depuis la DB."""
    _inject_login_css()

    st.session_state.setdefault("login_mode", "signin")
    st.session_state.setdefault("show_forgot", False)
    
    # Utiliser le vrai logo Ooredoo officiel
    from src.dashboard.logo import LOGO_B64

    with st.container(key="login_card"):
        left, right = st.columns([1.1, 1], gap="small")
        
        # PANNEAU GAUCHE - Branding
        with left:
            with st.container(key="login_left"):
                # Contenu du panneau gauche en HTML pur
                st.markdown(f'''
                <div class="login-left-content">
                    <img src="data:image/png;base64,{LOGO_B64}" alt="Ooredoo" class="wordmark">
                    <div class="brand-title">AI Benchmarking Dashboard</div>
                    <div class="brand-subtitle">
                        Évaluez, comparez et pilotez la performance des modèles IA 
                        sur des cas d'usage métier réels.
                    </div>
                </div>
                ''', unsafe_allow_html=True)
        
        # PANNEAU DROIT - Formulaire (widgets Streamlit)
        with right:
            with st.container(key="login_right"):
                # Wrapper pour centrer le formulaire
                st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
                
                if st.session_state.get("show_forgot"):
                    # Mode "Mot de passe oublié"
                    st.markdown("## Mot de passe oublié ?")
                    st.markdown('<div class="form-subtitle">Contactez votre administrateur pour réinitialiser votre mot de passe.</div>', unsafe_allow_html=True)
                    
                    st.markdown('<div class="back-button">', unsafe_allow_html=True)
                    if st.button("← Retour à la connexion", key="back_from_forgot"):
                        st.session_state["show_forgot"] = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                elif st.session_state["login_mode"] == "signin":
                    # Mode CONNEXION
                    st.markdown('## Connexion')
                    st.markdown('<div class="form-subtitle">Connectez-vous avec vos identifiants</div>', unsafe_allow_html=True)

                    with st.form("signin_form"):
                        email = st.text_input("Adresse e-mail", placeholder="vous@ooredoo.tn")
                        password = st.text_input("Mot de passe", type="password")
                        submitted = st.form_submit_button("Se connecter", use_container_width=True)
                    
                    if submitted:
                        logger.info(f"Login form submitted for email: {email}")
                        
                        try:
                            login_success = do_login(email, password)
                            
                            if login_success:
                                logger.info(f"Login successful, redirecting user: {email}")
                                st.success("✅ Connexion réussie !")
                                import time
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                logger.warning(f"Login failed for user: {email}")
                                
                        except Exception as e:
                            logger.error(f"Unexpected error during login: {e}", exc_info=True)
                            st.error("Une erreur inattendue s'est produite.")
                    
                    # Liens "Mot de passe oublié" et "Demander un accès"
                    st.markdown('<div class="form-links">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mot de passe oublié ?", key="forgot_btn"):
                            st.session_state["show_forgot"] = True
                            st.rerun()
                    with col2:
                        if st.button("Demander un accès", key="signup_btn"):
                            st.session_state["login_mode"] = "signup"
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    # Mode INSCRIPTION
                    st.markdown('## Demander un accès')
                    st.markdown('<div class="form-subtitle">Créez votre compte client</div>', unsafe_allow_html=True)
                    
                    # Récupérer les départements depuis la table scenarios
                    with engine.connect() as conn:
                        departments_result = conn.execute(text(
                            "SELECT DISTINCT departement FROM scenarios ORDER BY departement"
                        )).fetchall()
                        departments = [row[0] for row in departments_result]
                    
                    with st.form("signup_form"):
                        email = st.text_input("Adresse e-mail")
                        nom_complet = st.text_input("Nom complet")
                        departement = st.selectbox("Département", options=departments)
                        password = st.text_input("Mot de passe", type="password")
                        confirm = st.text_input("Confirmer le mot de passe", type="password")
                        submitted = st.form_submit_button("Créer un compte", use_container_width=True)
                    
                    if submitted:
                        logger.info(f"Signup form submitted for email: {email}")
                        
                        try:
                            signup_success = do_signup(email, nom_complet, departement, password, confirm)
                            
                            if signup_success:
                                # Pas de connexion automatique, message affiché par do_signup
                                pass
                            else:
                                logger.warning(f"Signup failed for user: {email}")
                                
                        except Exception as e:
                            logger.error(f"Unexpected error during signup: {e}", exc_info=True)
                            st.error("Une erreur inattendue s'est produite lors de la création du compte.")
                    
                    # Bouton retour
                    st.markdown('<div class="back-button">', unsafe_allow_html=True)
                    if st.button("← Retour à la connexion", key="back_signin"):
                        st.session_state["login_mode"] = "signin"
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # Messages d'erreur/succès
                if st.session_state.get("login_error"):
                    st.error(st.session_state["login_error"])
                
                if st.session_state.get("signup_success"):
                    st.success(st.session_state["signup_success"])
                    st.session_state["signup_success"] = None
                
                st.markdown('</div>', unsafe_allow_html=True)  # Fermer login-form-container


def render_sidebar_identity(email: str, role: str) -> None:
    """Render user identity at the BOTTOM of sidebar (no top banner)"""
    # This function now only handles the bottom identity section
    # The banner has been removed to clean up the UI
    pass  # Identity will be rendered at the end of sidebar in main()


def render_sidebar_user_bottom(email: str, role: str) -> None:
    """Render user profile and logout at the very bottom of the sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        <div style='text-align:center; padding:16px 0 8px 0;'>
            <div style='font-weight:600; font-size:14px; color:#1a1a1a;'>{email}</div>
            <div style='font-size:11px; letter-spacing:0.5px; color:#666; margin-top:4px;'>
                {role.upper()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Add password change button
    if st.sidebar.button("🔑 Changer mon mot de passe", use_container_width=True):
        st.session_state["show_password_change"] = True
    
    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.pop("auth_email", None)
        st.session_state.pop("auth_role", None)
        st.session_state.pop("auth_role_key", None)
        st.session_state.pop("auth_user_id", None)
        st.session_state.pop("auth_department", None)
        st.session_state.pop("login_mode", None)
        st.session_state.pop("show_password_change", None)
        st.rerun()
    
    role_messages = {
        "Client": "Vue simplifiée : indicateurs clés uniquement.",
        "Admin": "Accès complet aux données métier et aux exports.",
        "Super Admin": "Accès complet + outils d'administration.",
    }
    if role in role_messages:
        st.sidebar.caption(role_messages[role])

# ---------------------------------------------------------------------------
# Main app (post-login)
# ---------------------------------------------------------------------------

def main() -> None:
    """Main dashboard application with comprehensive error handling."""
    try:
        if "auth_role" not in st.session_state:
            login_page()
            st.stop()

        email = st.session_state["auth_email"]
        role = st.session_state["auth_role"]
        role_key = st.session_state.get("auth_role_key", "client")  # DB role key
        is_admin = role_key in ["admin", "super_admin"]
        is_super_admin = role_key == "super_admin"
        is_client = role_key == "client"
        
        logger.info(f"Dashboard accessed by user: {email} with role: {role_key}")

        # Show password change modal if requested
        if st.session_state.get("show_password_change"):
            with st.container():
                change_password_form()
                if st.button("← Retour au dashboard"):
                    st.session_state["show_password_change"] = False
                    st.rerun()
            st.stop()

        # === ROUTAGE CLIENT STRICT ===
        # Le client n'a accès à AUCUNE donnée brute, ni filtres, ni onglets, ni vocabulaire technique.
        # Il est immédiatement redirigé vers sa page dédiée et isolée par requête SQL.
        if is_client:
            render_client_recommendation_page(email)
            st.stop()

        render_sidebar_identity(email, role)

        if is_admin:
            if st.session_state.get("api_token"):
               st.sidebar.caption("API token: ✅ présent")
            else:
                st.sidebar.error(f"API token absent — erreur : {st.session_state.get('api_token_error')}")
                logger.warning(f"Admin user {email} missing API token: {st.session_state.get('api_token_error')}")

        # === CUSTOM CSS: Ooredoo Branding & Modern UI ===
        st.markdown(
            """
            <style>
            /* Primary Ooredoo Red */
            :root {
                --ooredoo-red: #ED1C24;
                --ooredoo-red-dark: #A80F17;
                --card-bg: #F8F9FA;
                --border-light: #E0E0E0;
            }
            
            /* KPI Cards Styling */
            div[data-testid="stMetric"] {
                background: var(--card-bg);
                border: 1px solid var(--border-light);
                border-radius: 8px;
                padding: 16px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            
            div[data-testid="stMetric"] label {
                font-size: 13px !important;
                font-weight: 600 !important;
                color: #666 !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                font-size: 28px !important;
                font-weight: 700 !important;
                color: #1a1a1a !important;
            }
            
            /* Primary Buttons */
            .stButton > button {
                background-color: var(--ooredoo-red) !important;
                color: white !important;
                border: none !important;
                font-weight: 600 !important;
                transition: all 0.2s ease;
            }
            
            .stButton > button:hover {
                background-color: var(--ooredoo-red-dark) !important;
                box-shadow: 0 4px 8px rgba(237, 28, 36, 0.3) !important;
            }
            
            /* Tabs Styling */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
            }
            
            .stTabs [data-baseweb="tab"] {
                height: 50px;
                padding: 0 24px;
                font-weight: 600;
                border-radius: 8px 8px 0 0;
            }
            
            .stTabs [aria-selected="true"] {
                background-color: var(--ooredoo-red) !important;
                color: white !important;
            }
            
            /* Sidebar Multiselect compact styling */
            .stMultiSelect {
                margin-bottom: 12px;
            }
            
            /* Header pill styling */
            .header-pill {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
                margin-left: 16px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # === HEADER ROW: Logo | Title | Last Execution Timestamp ===
        header_col1, header_col2, header_col3 = st.columns([1, 3, 2])
        
        with header_col1:
            st.markdown(
                f'<img src="data:image/png;base64,{LOGO_B64}" style="width:120px; margin-top:8px;">',
                unsafe_allow_html=True
            )
        
        with header_col2:
            st.markdown(
                """
                <div style="padding-top:16px;">
                    <span style="font-size:28px; color:#1a1a1a; font-weight:700;">Benchmark IA</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with header_col3:
            # Get last execution timestamp
            try:
                with engine.connect() as conn:
                    last_exec = pd.read_sql(
                        text("SELECT MAX(date_execution) as last_date FROM executions"),
                        conn
                    )
                    if not last_exec.empty and pd.notna(last_exec.iloc[0]["last_date"]):
                        last_date = pd.to_datetime(last_exec.iloc[0]["last_date"])
                        st.markdown(
                            f'<div style="padding-top:20px; text-align:right;">'
                            f'<span class="header-pill">📅 Dernière exécution: {last_date.strftime("%d/%m/%Y %H:%M")}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
            except Exception as e:
                logger.error(f"Error fetching last execution date: {e}")

        st.markdown("---")

        st.markdown(
            """
            <style>
            header {display:none;}
            h1 {font-size:30px; color:#ED1C29;}
            h2 {color:#ED1C29;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Load data with error handling
        try:
            st.sidebar.header("Filtres")
            load_all = st.sidebar.checkbox(
                "Charger toutes les exécutions (ignorer la limite)",
                value=False,
                help="Utile pour être sûr de voir tous les scénarios/modèles, même au-delà de la limite ci-dessous.",
            )
            if load_all:
                limit = None
                st.sidebar.caption("Limite désactivée — toutes les exécutions de la base sont chargées.")
            else:
                limit = st.sidebar.slider(
                    "Nombre d'exécutions à charger",
                    min_value=10,
                    max_value=2000,
                    value=300,
                    step=10,
                )

            # Load data with error handling
            with st.spinner("Chargement des données..."):
                df = load_executions(limit=limit)
                df = format_datetime(df)

            if df.empty:
                st.warning("Aucune exécution disponible dans la base de données.")
                st.info("Veuillez vérifier que des benchmarks ont été exécutés ou contactez votre administrateur.")
                return

            logger.info(f"Loaded {len(df)} executions for dashboard display")
            
        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}", exc_info=True)
            st.error("Erreur lors du chargement des données. Veuillez réessayer ou contactez votre administrateur.")
            st.exception(e)
            return

        # Continue with the rest of the main function...
        # (The rest remains unchanged for now, but with proper error handling wrapping)
        
    except Exception as e:
        logger.error(f"Critical error in main dashboard: {e}", exc_info=True)
        st.error("Une erreur critique s'est produite dans le dashboard.")
        st.error("Détails de l'erreur (pour débogage) :")
        st.exception(e)
        
        # Show recovery options
        with st.expander("Options de récupération"):
            if st.button("Réinitialiser la session"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            if st.button("Vider le cache"):
                st.cache_data.clear()
                st.success("Cache vidé. Veuillez actualiser la page.")
                
        return

    # Vérifier la présence de scores heuristiques anciens et prévenir
    try:
        with engine.connect() as conn:
            legacy_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)"
                )
            ).scalar()
    except Exception:
        legacy_count = 0

# if is_admin and legacy_count and legacy_count > 0:
#     st.sidebar.warning(
#         f"Attention — {legacy_count} scores heuristiques anciens détectés en base.\n"
#         "Ces anciennes métriques peuvent fausser les agrégations. Exécutez `python scripts/cleanup_scores.py --dry-run` puis `--apply` pour nettoyer."
#     )

    # Check for unevaluated (orphan) executions and warn
    try:
        with engine.connect() as conn:
            orphan_stats = conn.execute(
                text("""
                    SELECT 
                        COUNT(DISTINCT e.id) as total_executions,
                        COUNT(DISTINCT CASE WHEN (
                            SELECT COUNT(DISTINCT sc.critere)
                            FROM scores sc
                            WHERE sc.execution_id = e.id
                              AND sc.methode = 'ragas'
                              AND COALESCE(sc.is_legacy, FALSE) = FALSE
                              AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                              AND sc.note BETWEEN 0 AND 1
                        ) >= 1 THEN e.id END) as scored_executions
                    FROM executions e
                """)
            ).fetchone()
            total_exec = orphan_stats[0] or 0
            scored_exec = orphan_stats[1] or 0
            orphan_count = total_exec - scored_exec
    except Exception:
        orphan_count = 0
        total_exec = 0
        scored_exec = 0

    if orphan_count > 0:
        pct = round(orphan_count / total_exec * 100) if total_exec > 0 else 0
        st.info(
            f"ℹ️ **{orphan_count} exécution(s) en attente d'évaluation RAGAS complète** ({pct}% du total).\n\n"
            f"Les résultats affichés couvrent les {scored_exec} exécutions pleinement évaluées (sur {total_exec} au total). "
            f"Lancez `python reevaluate_missing_scores.py --resume` pour évaluer les restantes."
        )

    if df.empty:
        st.warning("Aucune exécution disponible dans la base de données.")
        return

    if is_admin:
        modeles = df["modele_nom"].unique().tolist()

        scenario_catalog = load_scenario_catalog()
        
        # === CASCADING FILTERS: Département -> Scénarios ===
        st.sidebar.markdown("### 🔍 Filtres")
        
        # Step 1: Select Départements
        all_departements = sorted(scenario_catalog["departement"].unique().tolist())
        selected_departements = st.sidebar.multiselect(
            "Départements",
            all_departements,
            default=all_departements,
            help="Filtrer par département (cascade vers les scénarios)"
        )
        
        # Step 2: Filter scenarios by selected departments
        if selected_departements:
            filtered_scenarios = scenario_catalog[
                scenario_catalog["departement"].isin(selected_departements)
            ]
        else:
            filtered_scenarios = scenario_catalog
        
        scenarios = filtered_scenarios["nom_cas_usage"].tolist()
        departement_par_scenario = dict(zip(
            filtered_scenarios["nom_cas_usage"], 
            filtered_scenarios["departement"]
        ))

        selected_modeles = st.sidebar.multiselect(
            "Modèles", 
            modeles, 
            default=modeles,
            help="Sélectionner les modèles à comparer"
        )
        
        selected_scenarios = st.sidebar.multiselect(
            "Scénarios",
            scenarios,
            default=scenarios,
            format_func=lambda nom: f"{nom[:40]}... ({departement_par_scenario.get(nom, '?')})" 
                if len(nom) > 40 
                else f"{nom} ({departement_par_scenario.get(nom, '?')})",
            help="Scénarios filtrés par les départements sélectionnés ci-dessus"
        )
  
        min_date = df["date_execution"].min().date()
        max_date = df["date_execution"].max().date()
        date_range = st.sidebar.date_input(
            "Période d'exécution",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filtrer les exécutions par période"
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date

    else:
        # Client : pas de filtres avancés, vue simplifiée sur toutes les données disponibles
        selected_modeles = df["modele_nom"].unique().tolist()
        selected_scenarios = df["nom_cas_usage"].unique().tolist()
        start_date = df["date_execution"].min().date()
        end_date = df["date_execution"].max().date()
        
    filtered = df[
        df["modele_nom"].isin(selected_modeles)
        & df["nom_cas_usage"].isin(selected_scenarios)
        & (df["date_execution"].dt.date >= start_date)
        & (df["date_execution"].dt.date <= end_date)
    ]

    # Style / affichage — advanced display controls are admin-only; regular
    # users get sensible defaults instead of being shown extra knobs.
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Affichage & style**")
        palette = st.sidebar.selectbox(
            "Palette de couleurs",
            options=["tableau10", "category10", "viridis", "blues", "inferno"],
            index=0,
        )
        normalize_stacked = st.sidebar.checkbox("Normaliser la pile (proportions)", value=False)
    else:
        palette = "tableau10"
        normalize_stacked = False

    # Advanced export controls
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Export avancé**")
        all_columns = filtered.columns.tolist()
        default_cols = [c for c in ["execution_id", "modele_nom", "nom_cas_usage", "date_execution", "score_global_display"] if c in all_columns]
        selected_columns_for_export = st.sidebar.multiselect("Colonnes à exporter", options=all_columns, default=default_cols)
    else:
        selected_columns_for_export = ["date_execution", "modele_nom", "nom_cas_usage", "score_global_display"]

    # === RENDER USER IDENTITY AT BOTTOM OF SIDEBAR ===
    render_sidebar_user_bottom(email, role)

    if filtered.empty:
        st.warning("Aucun résultat pour les filtres sélectionnés et la période définie.")
        return

    latest_run = filtered["date_execution"].max()
    st.caption(f"Dernière exécution chargée : {latest_run}")

    metric_names = {
        "score_global_display": "Score global",
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer relevancy",
        "context_precision": "Context precision",
        "context_recall": "Context recall",
        "latence_secondes": "Latence (s)",
    }
    selected_metric_key = st.sidebar.selectbox(
        "Métrique à comparer",
        list(metric_names.values()),
        index=0,
    )
    selected_metric = next(
        key for key, label in metric_names.items() if label == selected_metric_key
    )

    summary_model = (
        filtered.groupby("modele_nom")[
            ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall", "latence_secondes"]
        ]
        .mean()
        .round(3)
        .reset_index()
        .sort_values("score_global_display", ascending=False)
    )

    summary_scenario = (
        filtered.groupby("nom_cas_usage")[
            ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall", "latence_secondes"]
        ]
        .mean()
        .round(3)
        .reset_index()
        .sort_values("score_global_display", ascending=False)
    )

    model_metrics_long = summary_model.melt(
        id_vars=["modele_nom"],
        value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        var_name="critere",
        value_name="note",
    )

    best_model = summary_model.iloc[0] if not summary_model.empty else None
    best_scenario = summary_scenario.iloc[0] if not summary_scenario.empty else None

    # ------------------------------------------------------------------
    # Construction des onglets : le Client n'a plus "Détails des
    # exécutions" (données brutes/techniques) ni "Pilotage".
    # ------------------------------------------------------------------
    tabs = ["Vue d'ensemble", "Comparaison modèles", "Comparaison scénarios", "Détails des exécutions"]

    if is_admin:
        tabs.append("Pilotage")
    if is_super_admin:
        tabs.append("Administration")

    tab_objects = st.tabs(tabs)

    overview_tab, models_tab, scenarios_tab, details_tab = tab_objects[:4]
    extra_tabs = list(tab_objects[4:])

    pilotage_tab = extra_tabs.pop(0) if is_admin else None
    admin_tab = extra_tabs.pop(0) if is_super_admin else None

    with overview_tab:
        if role == "Client":
            st.markdown("## Vue d'ensemble")
            

            st.markdown("#### Top 3 modèles")
            top3 = summary_model.head(3).copy()
            if not top3.empty:
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                top3["Qualité"] = top3["score_global_display"].apply(score_to_label)
                top3["score_global_display"] = top3["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(
                    top3.rename(
                        columns={
                            "modele_nom": "Modèle",
                            "score_global_display": "Score global",
                            "latence_secondes": "Latence (s)",
                        }
                    )[["Modèle", "Qualité", "Latence (s)"]]
                )
            else:
                st.info("Pas de modèles à afficher pour le Top 3.")

            st.markdown("#### Top 3 scénarios")
            top3_scenarios = summary_scenario.head(3).copy()
            if not top3_scenarios.empty:
                top3_scenarios = top3_scenarios.reset_index(drop=True)
                top3_scenarios.index = top3_scenarios.index + 1
                top3_scenarios["Qualité"] = top3_scenarios["score_global_display"].apply(score_to_label)
                top3_scenarios["score_global_display"] = top3_scenarios["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(
                    top3_scenarios.rename(
                        columns={
                            "nom_cas_usage": "Scénario",
                            "score_global_display": "Score global",
                            "latence_secondes": "Latence (s)",
                        }
                    )[["Scénario", "Qualité", "Latence (s)"]]
                )
            else:
                st.info("Pas de scénarios à afficher pour le Top 3.")

            st.divider()
            build_client_department_comparison(filtered)
        else:
            build_metric_cards(filtered, client_mode=False, total_executions_in_db=total_exec)
            daily_mean = (
                filtered.dropna(subset=["score_global_display"])
                .groupby(pd.Grouper(key="date_execution", freq="D"))["score_global_display"]
                .mean()
                .reset_index()
            )
            if not daily_mean.empty:
                st.markdown("#### Tendance moyenne des scores")
                st.vega_lite_chart(
                    data=daily_mean,
                    spec={
                        # Point-only mark: avoids connecting lines between sparse
                        # dates which would imply false continuity between days
                        # that have zero executions in between.
                        "mark": {"type": "point", "filled": True, "size": 80},
                        "encoding": {
                            "x": {"field": "date_execution", "type": "temporal", "title": "Date"},
                            "y": {
                                "field": "score_global_display",
                                "type": "quantitative",
                                "title": "Score moyen",
                                "scale": {"domain": [0, 1]},
                            },
                            "tooltip": [
                                {"field": "date_execution", "type": "temporal", "title": "Date"},
                                {"field": "score_global_display", "type": "quantitative",
                                 "title": "Score moyen", "format": ".1%"},
                            ],
                        },
                    },
                    use_container_width=True,
                )
            st.divider()

            if best_model is not None and best_scenario is not None:
                rec_col1, rec_col2, rec_col3 = st.columns([3, 3, 2])
                second_score = summary_model.iloc[1]["score_global_display"] if len(summary_model) > 1 else 0
                delta = best_model["score_global_display"] - second_score
                rec_col1.metric(
                    "Modèle recommandé",
                    f"{best_model['modele_nom']} ({best_model['score_global_display']:.3f})",
                    delta=f"{delta:+.3f}",
                )
                rec_col2.metric(
                    "Scénario recommandé",
                    best_scenario["nom_cas_usage"],
                    f"{best_scenario['score_global_display']:.3f}",
                )
                rec_col3.metric(
                    "Scores évalués",
                    int(filtered[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].count().sum()),
                )
            st.divider()

            st.markdown("#### Top 3 modèles")
            top3 = summary_model.head(3).copy()
            if not top3.empty:
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                for _score_col in ["score_global_display", "faithfulness", "answer_relevancy",
                                   "context_precision", "context_recall"]:
                    if _score_col in top3.columns:
                        top3[_score_col] = top3[_score_col].apply(safe_format_score)
                top3["latence_secondes"] = top3["latence_secondes"].map(lambda v: f"{v:.2f}s")
                st.table(
                    top3.rename(
                        columns={
                            "modele_nom": "Modèle",
                            "score_global_display": "Score global",
                            "faithfulness": "Faithfulness",
                            "answer_relevancy": "Answer relevancy",
                            "context_precision": "Context precision",
                            "context_recall": "Context recall",
                            "latence_secondes": "Latence (s)",
                        }
                    )
                )
            else:
                st.info("Pas de modèles à afficher pour le Top 3.")

            st.markdown("#### Meilleur modèle par scénario")
            best_per_scenario = (
                filtered.dropna(subset=["score_global_display"])
                .groupby(["nom_cas_usage", "modele_nom"])["score_global_display"]
                .mean()
                .reset_index()
                .sort_values(["nom_cas_usage", "score_global_display"], ascending=[True, False])
                .groupby("nom_cas_usage")
                .first()
                .reset_index()
            )
            if not best_per_scenario.empty:
                best_per_scenario["score_global_display"] = best_per_scenario["score_global_display"].apply(safe_format_score)
                st.table(best_per_scenario.rename(columns={"nom_cas_usage": "Scénario", "modele_nom": "Meilleur modèle", "score_global_display": "Score"}))
            else:
                st.info("Pas assez de données pour déterminer le meilleur modèle par scénario.")
            st.divider()

            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exporter CSV des exécutions filtrées",
                data=csv,
                file_name="executions_filtered.csv",
                mime="text/csv",
            )
            if is_admin:
                try:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                        if selected_columns_for_export:
                            filtered[selected_columns_for_export].to_excel(writer, index=False, sheet_name="executions")
                        else:
                            filtered.to_excel(writer, index=False, sheet_name="executions")
                        summary_model.to_excel(writer, index=False, sheet_name="summary_model")
                        summary_scenario.to_excel(writer, index=False, sheet_name="summary_scenario")
                    excel_bytes = excel_buffer.getvalue()
                    st.download_button(
                        "Exporter Excel multi-feuilles (xlsx)",
                        data=excel_bytes,
                        file_name="executions_filtered_multi.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception:
                    st.info("Export Excel non disponible (vérifiez que 'openpyxl' est installé).")

            st.markdown("#### Répartition des métriques RAGAS par modèle (stacked)")
            stacked_df = model_metrics_long.rename(columns={"modele_nom": "Modèle", "critere": "Critère", "note": "Note"})
            if not stacked_df.empty:
                stacked_spec = {
                    "mark": "bar",
                    "encoding": {
                        "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                        "x": {"aggregate": "sum", "field": "Note", "type": "quantitative"},
                        "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative"},
                        ],
                    },
                }
                if normalize_stacked:
                    stacked_spec["encoding"]["x"]["stack"] = "normalize"
                st.vega_lite_chart(data=stacked_df, spec=stacked_spec, use_container_width=True)
            else:
                st.info("Aucune donnée RAGAS disponible pour le stacked chart.")

            st.markdown("#### Heatmap : score global (scénarios × modèles)")
            heat_order = st.selectbox("Trier heatmap par", options=["Aucun", "Moyenne modèle", "Moyenne scénario"], index=1)
            heat_df = (
                filtered.pivot_table(
                    index="nom_cas_usage", columns="modele_nom", values="score_global_display", aggfunc="mean"
                )
                .reset_index()
                .melt(id_vars=["nom_cas_usage"], var_name="modele_nom", value_name="score")
            )
            heat_df = heat_df.rename(columns={"nom_cas_usage": "Scénario", "modele_nom": "Modèle", "score": "Score"})
            if not heat_df["Score"].isna().all():
                if heat_order == "Moyenne modèle":
                    order = summary_model["modele_nom"].tolist()
                    heat_df["Modèle"] = pd.Categorical(heat_df["Modèle"], categories=order, ordered=True)
                elif heat_order == "Moyenne scénario":
                    scen_order = summary_scenario["nom_cas_usage"].tolist()
                    heat_df["Scénario"] = pd.Categorical(heat_df["Scénario"], categories=scen_order, ordered=True)
                heat_spec = {
                    "mark": "rect",
                    "encoding": {
                        "x": {"field": "Modèle", "type": "nominal"},
                        "y": {"field": "Scénario", "type": "nominal"},
                        "color": {"field": "Score", "type": "quantitative", "scale": {"scheme": palette}},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Score", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=heat_df, spec=heat_spec, use_container_width=True)
            else:
                st.info("Aucune donnée de score global pour produire la heatmap.")

            st.markdown("#### Distributions : score global et latence")
            hist_col1, hist_col2 = st.columns(2)
            score_hist_df = filtered["score_global_display"].dropna().to_frame(name="Score")
            latency_hist_df = filtered["latence_secondes"].dropna().to_frame(name="Latence")
            if not score_hist_df.empty:
                hist_col1.vega_lite_chart(
                    data=score_hist_df,
                    spec={
                        "mark": "bar",
                        "encoding": {"x": {"field": "Score", "type": "quantitative", "bin": True}, "y": {"aggregate": "count", "type": "quantitative"}},
                    },
                    use_container_width=True,
                )
            else:
                hist_col1.info("Pas de scores pour l'histogramme.")

            if not latency_hist_df.empty:
                hist_col2.vega_lite_chart(
                    data=latency_hist_df,
                    spec={
                        "mark": "bar",
                        "encoding": {"x": {"field": "Latence", "type": "quantitative", "bin": True}, "y": {"aggregate": "count", "type": "quantitative"}},
                    },
                    use_container_width=True,
                )
            else:
                hist_col2.info("Pas de latences pour l'histogramme.")
            st.divider()

    with scenarios_tab:

        if role == "Client":
            st.markdown("## Comparaison scénarios")
            st.write("Vue simplifiée des scénarios les plus performants.")
            simple_scenarios = summary_scenario[["nom_cas_usage", "score_global_display"]].head(5).copy()
            simple_scenarios["Qualité"] = simple_scenarios["score_global_display"].apply(score_to_label)
            st.table(
                simple_scenarios.rename(
                    columns={
                        "nom_cas_usage": "Scénario",
                        "score_global_display": "Score global",
                    }
                )[["Scénario", "Qualité"]]
            )
        else:
            st.markdown("## Comparaison des scénarios")
            st.write("Comparez les scénarios par score global, métriques dimensions et pertinence.")
            _display_scenario = summary_scenario.copy()
            for _col in ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                if _col in _display_scenario.columns:
                    _display_scenario[_col] = _display_scenario[_col].apply(lambda x: safe_format_score(x, as_percentage=True))
            if "latence_secondes" in _display_scenario.columns:
                _display_scenario["latence_secondes"] = _display_scenario["latence_secondes"].apply(safe_format_latency)
            st.dataframe(_display_scenario, use_container_width=True)
            st.divider()
            st.markdown("### Top scénarios par score global")
            st.vega_lite_chart(
                data=summary_scenario.rename(columns={"nom_cas_usage": "Scénario", "score_global_display": "Score global"}).head(5),
                spec={
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Score global", "type": "quantitative"},
                        "y": {"field": "Scénario", "type": "nominal", "sort": "-x"},
                        "tooltip": [
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Score global", "type": "quantitative"},
                        ],
                    },
                },
                use_container_width=True,
            )
            st.divider()
            st.markdown("### Comparaison des critères RAGAS par scénario")
            metrics_by_scenario = summary_scenario.melt(
                id_vars=["nom_cas_usage"],
                value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
                var_name="Critère",
                value_name="Note",
            ).rename(columns={"nom_cas_usage": "Scénario"})
            st.vega_lite_chart(
                data=metrics_by_scenario,
                spec={
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "Note",
                            "type": "quantitative",
                            "scale": {"domain": [0, 1]},
                            "title": "Score (0–1)",
                        },
                        "y": {"field": "Scénario", "type": "nominal", "sort": "-x"},
                        # xOffset groups bars by Critère instead of stacking them.
                        # Without this, Vega-Lite stacks the 4 metrics by default,
                        # producing x-axis totals up to 4.0.
                        "xOffset": {"field": "Critère"},
                        "color": {
                            "field": "Critère",
                            "type": "nominal",
                            "scale": {"scheme": palette},
                        },
                        "tooltip": [
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative", "format": ".1%"},
                        ],
                    },
                },
                use_container_width=True,
            )
            st.divider()
            st.markdown("### Top 3 scénarios")
            _top3_scen = summary_scenario.head(3).copy()
            for _score_col in ["score_global_display", "faithfulness", "answer_relevancy",
                               "context_precision", "context_recall"]:
                if _score_col in _top3_scen.columns:
                    _top3_scen[_score_col] = _top3_scen[_score_col].apply(safe_format_score)
            if "latence_secondes" in _top3_scen.columns:
                _top3_scen["latence_secondes"] = _top3_scen["latence_secondes"].apply(safe_format_latency)
            st.table(_top3_scen.rename(
                columns={
                    "nom_cas_usage": "Scénario",
                    "score_global_display": "Score global",
                    "faithfulness": "Faithfulness",
                    "answer_relevancy": "Answer relevancy",
                    "context_precision": "Context precision",
                    "context_recall": "Context recall",
                    "latence_secondes": "Latence (s)",
                }
            ))


    with models_tab:
        if role == "Client":
            build_client_department_comparison(filtered)
            st.divider()
            st.markdown("## Comparaison modèles (vue simplifiée)")
            simple_model_table = summary_model[["modele_nom", "score_global_display", "latence_secondes"]].copy()
            simple_model_table["Qualité"] = simple_model_table["score_global_display"].apply(score_to_label)
            simple_model_table["latence_secondes"] = simple_model_table["latence_secondes"].map(lambda v: f"{v:.2f}s")
            st.table(
                simple_model_table.rename(
                    columns={
                        "modele_nom": "Modèle",
                        "latence_secondes": "Latence (s)",
                    }
                )[["Modèle", "Qualité", "Latence (s)"]]
            )
        else:
            st.markdown("## Comparaison modèles")
            st.write("Comparez les modèles par score global, métriques RAGAS, et latence.")
            _display_model = summary_model.copy()
            for _col in ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                if _col in _display_model.columns:
                    _display_model[_col] = _display_model[_col].apply(lambda x: safe_format_score(x, as_percentage=True))
            if "latence_secondes" in _display_model.columns:
                _display_model["latence_secondes"] = _display_model["latence_secondes"].apply(safe_format_latency)
            st.dataframe(_display_model, use_container_width=True)
            st.divider()
            st.markdown("### Comparaison des critères RAGAS par modèle")
            chart_mode = st.selectbox("Type de graphique RAGAS", options=["Barres groupées", "Barres empilées", "Barres empilées normalisées", "Barres horizontales"], index=0)
            group_by_metric = st.checkbox("Afficher par métrique (small multiples)", value=False)
            metrics_by_model = summary_model.melt(
                id_vars=["modele_nom"],
                value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
                var_name="Critère",
                value_name="Note",
            ).rename(columns={"modele_nom": "Modèle"})
            if group_by_metric:
                small_spec = {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Note", "type": "quantitative"},
                        "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                        "color": {"field": "Modèle", "type": "nominal", "legend": None},
                        "column": {"field": "Critère", "type": "nominal"},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=metrics_by_model, spec=small_spec, use_container_width=True)
            else:
                if chart_mode == "Barres groupées":
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "x": {"field": "Note", "type": "quantitative"},
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                elif chart_mode == "Barres empilées" or chart_mode == "Barres empilées normalisées":
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "x": {"aggregate": "sum", "field": "Note", "type": "quantitative"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                    if chart_mode == "Barres empilées normalisées":
                        spec["encoding"]["x"]["stack"] = "normalize"
                else:
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "x": {"field": "Note", "type": "quantitative"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                st.vega_lite_chart(data=metrics_by_model, spec=spec, use_container_width=True)
            st.divider()
            st.markdown("### Distribution des scores par modèle")
            box_df = filtered[["modele_nom", "score_global_display"]].dropna()
            if not box_df.empty:
                box_spec = {
                    "mark": "boxplot",
                    "encoding": {
                        "x": {"field": "modele_nom", "type": "nominal", "title": "Modèle"},
                        "y": {"field": "score_global_display", "type": "quantitative", "title": "Score global"},
                        "color": {"field": "modele_nom", "type": "nominal", "legend": None},
                    },
                }
                st.vega_lite_chart(data=box_df, spec=box_spec, use_container_width=True)
            else:
                st.info("Pas assez de données pour afficher les distributions par modèle.")

            st.divider()
            st.markdown("### Tendance temporelle des meilleurs modèles")
            top_models = summary_model.head(5)["modele_nom"].tolist()
            ts_df = (
                filtered.dropna(subset=["score_global_display"])
                .groupby([pd.Grouper(key="date_execution", freq="D"), "modele_nom"])["score_global_display"]
                .mean()
                .reset_index()
            )
            if not ts_df.empty:
                ts_spec = {
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        "x": {"field": "date_execution", "type": "temporal", "title": "Date"},
                        "y": {"field": "score_global_display", "type": "quantitative", "title": "Score global"},
                        "color": {"field": "modele_nom", "type": "nominal", "title": "Modèle"},
                        "tooltip": [
                            {"field": "date_execution", "type": "temporal"},
                            {"field": "modele_nom", "type": "nominal"},
                            {"field": "score_global_display", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=ts_df[ts_df["modele_nom"].isin(top_models[:3])], spec=ts_spec, use_container_width=True)
            else:
                st.info("Pas de séries temporelles disponibles pour les scores.")

            st.divider()
            st.markdown("### Top 5 modèles — résumé")
            top5 = summary_model.head(5).copy()
            if not top5.empty:
                for _score_col in ["score_global_display", "faithfulness", "answer_relevancy",
                                   "context_precision", "context_recall"]:
                    if _score_col in top5.columns:
                        top5[_score_col] = top5[_score_col].apply(safe_format_score)
                top5["latence_secondes"] = top5["latence_secondes"].map(lambda v: f"{v:.2f}s")
                st.table(top5.rename(columns={
                    "modele_nom": "Modèle",
                    "score_global_display": "Score global",
                    "faithfulness": "Faithfulness",
                    "answer_relevancy": "Answer relevancy",
                    "context_precision": "Context precision",
                    "context_recall": "Context recall",
                    "latence_secondes": "Latence",
                }))
            else:
                st.info("Aucun modèle disponible pour le Top 5.")

    # ------------------------------------------------------------------
    # "Détails des exécutions" : réservé Admin / Super Admin uniquement
    # (données brutes/techniques retirées de l'interface Client).
    # ------------------------------------------------------------------
    
        with details_tab:
            st.markdown("## Détail des exécutions")
            st.write("Consultez la liste complète des exécutions récentes, puis sélectionnez une entrée pour voir la réponse et les scores détaillés.")

            display_columns = [
                "date_execution",
                "modele_nom",
                "nom_cas_usage",
                "departement",
                "latence_secondes",
                "cout_estime",
                "score_global_auto",
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
            ]
            
            # Format the data for display with proper None handling
            formatted_df = format_executions_for_display(
                filtered.sort_values("date_execution", ascending=False),
                display_columns
            )
            
            st.dataframe(
                formatted_df.rename(
                    columns={
                        "date_execution": "Date",
                        "modele_nom": "Modèle",
                        "nom_cas_usage": "Scénario",
                        "departement": "Département",
                        "latence_secondes": "Latence (s)",
                        "cout_estime": "Coût estimé",
                        "score_global_auto": "Score global",
                        "faithfulness": "Faithfulness",
                        "answer_relevancy": "Answer relevancy",
                        "context_precision": "Context precision",
                        "context_recall": "Context recall",
                    }
                ),
                use_container_width=True,
            )

            # Create rich labels for execution selectbox
            execution_options = filtered.sort_values("date_execution", ascending=False).copy()
            execution_ids = execution_options["execution_id"].tolist()
            
            def format_execution_label(exec_id):
                """Format execution selectbox label with rich context"""
                row = execution_options[execution_options["execution_id"] == exec_id].iloc[0]
                
                # Truncate scenario name if too long
                scenario = row["nom_cas_usage"]
                if len(scenario) > 50:
                    scenario = scenario[:47] + "..."
                
                # Format score with proper None handling
                score = row.get("score_global_auto")
                if score is not None and not pd.isna(score):
                    score_display = f"({score*100:.1f}%)"
                else:
                    score_display = "(N/A)"
                
                return f"#{exec_id} | {row['departement']} | {scenario} | {row['modele_nom']} {score_display}"
            
            selected_execution = st.selectbox(
                "Sélectionner une exécution",
                options=execution_ids,
                format_func=format_execution_label,
            )
            execution_data = filtered[filtered["execution_id"] == selected_execution].iloc[0]

            st.divider()
            st.markdown("### Exécution sélectionnée")
            left_col, right_col = st.columns(2)
            left_col.markdown(
                f"**Modèle** : {execution_data['modele_nom']}  \n"
                f"**Scénario** : {execution_data['nom_cas_usage']}  \n"
                f"**Département** : {execution_data['departement']}"
            )
            right_col.markdown(
                f"**Score global** : {safe_format_score(execution_data['score_global_auto'])}  \n"
                f"**Latence** : {safe_format_latency(execution_data['latence_secondes'])}  \n"
                f"**Coût estimé** : {safe_format_cost(execution_data['cout_estime'])}"
            )

            with st.expander("Réponse générée"):
                st.code(execution_data["reponse_generee"], language="text")

            st.markdown("### Notes d'évaluation")
            score_items = {
                "Faithfulness": execution_data.get("faithfulness"),
                "Answer relevancy": execution_data.get("answer_relevancy"),
                "Context precision": execution_data.get("context_precision"),
                "Context recall": execution_data.get("context_recall"),
            }
            
            # Display scores with proper None handling
            for label, value in score_items.items():
                formatted_value = safe_format_score(value)
                st.write(f"- **{label}** : {formatted_value}")
            
            # Display global score
            global_score = execution_data.get("score_global_auto")
            formatted_global = safe_format_score(global_score)
            st.write(f"- **Score Global** : {formatted_global}")

    if is_admin and pilotage_tab is not None:
        with pilotage_tab:
            st.markdown("## Pilotage du benchmark")
            st.write(
                "Déclenchez une nouvelle exécution du pipeline multi-agents et gérez le "
                "catalogue des scénarios et des modèles testés."
            )

            # -----------------------------------------------------------------
            # Lancer un nouveau benchmark
            # -----------------------------------------------------------------
            st.markdown("### Lancer un nouveau benchmark")
            st.caption(
                "Déclenche l'exécution du benchmark sur les scénarios des départements et modèles sélectionnés."
            )

            all_scenarios = admin_list_scenarios()
            selected_departements = st.multiselect(
                "Départements à exécuter",
                options=DEPARTEMENTS_OFFICIELS,
                default=DEPARTEMENTS_OFFICIELS,
                key="run_departements",
                help="Tous les scénarios du (des) département(s) sélectionné(s) seront inclus dans le benchmark.",
            )

            selected_scenario_ids = [
                s.id for s in all_scenarios 
                if DEPARTEMENTS_MAPPING.get(s.departement, s.departement) in selected_departements
            ]

            if selected_departements:
                nb = len(selected_scenario_ids)
                st.caption(f"→ {nb} scénario(s) au total pour {len(selected_departements)} département(s) sélectionné(s).")
            else:
                st.caption("⚠️ Veuillez sélectionner au moins un département.")

            selected_models = st.multiselect(
                "Modèles à tester",
                options=MODELES_DISPONIBLES,
                default=["llama3.1:8b", "mistral:7b"],
                key="run_model_names",
                help="Sélectionnez un ou plusieurs modèles testés et disponibles à évaluer.",
            )

            if st.button("🚀 Lancer le benchmark", key="run_benchmark_btn"):
                if not selected_departements:
                    st.error("Veuillez sélectionner au moins un département à exécuter.")
                elif not selected_scenario_ids:
                    st.error("Aucun scénario trouvé pour les départements sélectionnés.")
                elif not selected_models:
                    st.error("Veuillez sélectionner au moins un modèle à tester.")
                else:
                    nb_runs = len(selected_scenario_ids) * len(selected_models)
                    with st.status(
                        f"🚀 Exécution du benchmark en cours ({len(selected_scenario_ids)} scénarios × {len(selected_models)} modèles = {nb_runs} exécutions)...",
                        expanded=True,
                    ) as status_box:
                        st.write("🔄 Initialisation du pipeline multi-agents...")
                        st.write(f"📌 Départements sélectionnés : **{', '.join(selected_departements)}**")
                        st.write(f"🤖 Modèles sélectionnés : **{', '.join(selected_models)}**")
                        
                        progress_bar = st.progress(5, text="Initialisation du pipeline...")
                        live_status = st.empty()
                        log_container = st.empty()
                        
                        import threading
                        from pathlib import Path
                        
                        run_result = {}
                        def _bg_runner():
                            _ok, _res = trigger_benchmark_run(
                                scenario_ids=selected_scenario_ids,
                                model_names=selected_models,
                            )
                            run_result["ok"] = _ok
                            run_result["result"] = _res

                        t = threading.Thread(target=_bg_runner)
                        t.start()
                        
                        log_path = Path("logs/benchmark.log")
                        start_pos = log_path.stat().st_size if log_path.exists() else 0
                        total_expected = len(selected_scenario_ids) * len(selected_models)
                        completed_items = 0
                        recent_logs = []
                        
                        while t.is_alive():
                            if log_path.exists():
                                try:
                                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                                        f.seek(start_pos)
                                        new_data = f.read()
                                        if new_data:
                                            for line in new_data.splitlines():
                                                line_str = line.strip()
                                                if line_str:
                                                    recent_logs.append(line_str)
                                                    if "Scenario [" in line_str:
                                                        info = line_str.split(" - ")[-1] if " - " in line_str else line_str
                                                        live_status.info(f"⚡ **En cours :** `{info}`")
                                                    if "OK - Reponse generee" in line_str:
                                                        completed_items += 1
                                            recent_logs = recent_logs[-8:]
                                            log_container.code("\n".join(recent_logs), language="text")
                                except Exception:
                                    pass
                            pct = min(95, max(5, int((completed_items / max(total_expected, 1)) * 90)))
                            progress_bar.progress(pct, text=f"Progression : {completed_items}/{total_expected} scénarios traités ({pct}%)")
                            time.sleep(2)
                        
                        t.join()
                        progress_bar.progress(100, text="Traitement terminé !")
                        ok = run_result.get("ok", False)
                        result = run_result.get("result", "Erreur inattendue")
                        
                        if ok:
                            status_box.update(label="✅ Benchmark terminé avec succès !", state="complete", expanded=False)
                        else:
                            status_box.update(label="❌ Erreur lors de l'exécution du benchmark", state="error", expanded=True)

                    if ok:
                        st.success(f"🎉 **Benchmark terminé avec succès — statut : {result.get('status', 'completed')}**")
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Scénarios exécutés", result.get("nb_scenarios", len(selected_scenario_ids)))
                        m2.metric("Modèles testés", result.get("nb_models") or result.get("nb_modeles", len(selected_models)))
                        m3.metric("Exécutions produites", result.get("nb_executions", 0))
                        m4.metric("Statut", result.get("status", "completed"))
                        
                        if result.get("erreurs"):
                            st.warning("⚠️ Erreurs rencontrées pendant l'exécution :")
                            for err in result["erreurs"]:
                                st.write(f"- {err}")
                        if result.get("rapport"):
                            with st.expander("📊 Rapport détaillé (JSON)"):
                                st.json(result["rapport"])
                        
                        # Auto-clear cache to show new executions immediately
                        st.info("✅ Cache vidé automatiquement — les nouvelles données sont visibles dans tous les onglets.")
                        st.cache_data.clear()
                    else:
                        st.error(result)

            st.divider()

            # -----------------------------------------------------------------
            # Complétude du catalogue de scénarios (ajout)
            # -----------------------------------------------------------------
            st.markdown("### Complétude du catalogue de scénarios")
            st.caption(
                f"Cible : {SCENARIOS_CIBLE_PAR_DEPARTEMENT} scénarios par département, "
                "pour garantir une couverture suffisante des cas d'usage métier."
            )
            completeness_df = admin_scenarios_completeness()
            if not completeness_df.empty:
                st.dataframe(completeness_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun scénario en base pour l'instant.")

            st.divider()

            # -----------------------------------------------------------------
            # Catalogue des scénarios
            # -----------------------------------------------------------------
            st.markdown("### Catalogue des scénarios")
            scenarios = admin_list_scenarios()
            if scenarios:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "ID": s.id,
                                "Département": s.departement,
                                "Métier": s.metier,
                                "Cas d'usage": s.nom_cas_usage,
                            }
                            for s in scenarios
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Aucun scénario en base.")

            scen_manage_col, scen_create_col = st.columns(2)

            with scen_manage_col:
                st.markdown("#### Modifier / supprimer un scénario")
                if scenarios:
                    scen_labels = [f"{s.nom_cas_usage} ({s.departement})" for s in scenarios]
                    scen_idx = st.selectbox(
                        "Scénario",
                        options=range(len(scenarios)),
                        format_func=lambda i: scen_labels[i],
                        key="scen_selected",
                    )
                    sel_scen = scenarios[scen_idx]
                    with st.form("edit_scenario_form"):
                        e_departement = st.text_input("Département", value=sel_scen.departement)
                        e_metier = st.text_input("Métier", value=sel_scen.metier or "")
                        e_nom = st.text_input("Nom du cas d'usage", value=sel_scen.nom_cas_usage)
                        e_prompt = st.text_area("Prompt", value=sel_scen.prompt, height=120)
                        e_sortie = st.text_area("Sortie attendue", value=sel_scen.sortie_attendue or "")
                        e_critere = st.text_area("Critère de succès", value=sel_scen.critere_succes or "")
                        scen_update_submitted = st.form_submit_button("Mettre à jour")
                    if scen_update_submitted:
                        ok, msg = admin_update_scenario(
                            sel_scen.id, e_departement, e_metier, e_nom, e_prompt, e_sortie, e_critere
                        )
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()

                    if st.button("🗑️ Supprimer ce scénario", key="delete_scenario_btn"):
                        ok, msg = admin_delete_scenario(sel_scen.id)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()
                else:
                    st.info("Aucun scénario à gérer pour le moment.")

            with scen_create_col:
                st.markdown("#### Ajouter un scénario")
                with st.form("create_scenario_form"):
                    c_departement = st.text_input("Département", key="c_departement")
                    c_metier = st.text_input("Métier", key="c_metier")
                    c_nom = st.text_input("Nom du cas d'usage", key="c_nom")
                    c_prompt = st.text_area("Prompt", key="c_prompt", height=120)
                    c_sortie = st.text_area("Sortie attendue", key="c_sortie")
                    c_critere = st.text_area("Critère de succès", key="c_critere")
                    scen_create_submitted = st.form_submit_button("Créer le scénario")
                if scen_create_submitted:
                    ok, msg = admin_create_scenario(
                        c_departement, c_metier, c_nom, c_prompt, c_sortie, c_critere
                    )
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()

            st.divider()

            # -----------------------------------------------------------------
            # Catalogue des modèles
            # -----------------------------------------------------------------
            st.markdown("### Catalogue des modèles")
            models_catalog = admin_list_models()
            if models_catalog:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "ID": m.id,
                                "Nom": m.nom,
                                "Fournisseur": m.fournisseur,
                                "Version": m.version,
                                "Coût / 1k tokens": m.cout_par_1k_tokens,
                            }
                            for m in models_catalog
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Aucun modèle en base.")

            model_manage_col, model_create_col = st.columns(2)

            with model_manage_col:
                st.markdown("#### Modifier / supprimer un modèle")
                if models_catalog:
                    model_labels = [m.nom for m in models_catalog]
                    model_idx = st.selectbox(
                        "Modèle",
                        options=range(len(models_catalog)),
                        format_func=lambda i: model_labels[i],
                        key="model_selected",
                    )
                    sel_model = models_catalog[model_idx]
                    with st.form("edit_model_form"):
                        e_m_nom = st.text_input("Nom", value=sel_model.nom)
                        e_m_fournisseur = st.text_input("Fournisseur", value=sel_model.fournisseur or "")
                        e_m_version = st.text_input("Version", value=sel_model.version or "")
                        e_m_cout = st.number_input(
                            "Coût / 1k tokens",
                            value=float(sel_model.cout_par_1k_tokens or 0.0),
                            step=0.0001,
                            format="%.4f",
                        )
                        model_update_submitted = st.form_submit_button("Mettre à jour")
                    if model_update_submitted:
                        ok, msg = admin_update_model(sel_model.id, e_m_nom, e_m_fournisseur, e_m_version, e_m_cout)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()

                    if st.button("🗑️ Supprimer ce modèle", key="delete_model_btn"):
                        ok, msg = admin_delete_model(sel_model.id)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()
                else:
                    st.info("Aucun modèle à gérer pour le moment.")

            with model_create_col:
                st.markdown("#### Ajouter un modèle")
                with st.form("create_model_form"):
                    c_m_nom = st.text_input("Nom", key="c_m_nom")
                    c_m_fournisseur = st.text_input("Fournisseur", key="c_m_fournisseur")
                    c_m_version = st.text_input("Version", key="c_m_version")
                    c_m_cout = st.number_input("Coût / 1k tokens", key="c_m_cout", step=0.0001, format="%.4f")
                    model_create_submitted = st.form_submit_button("Ajouter le modèle")
                if model_create_submitted:
                    ok, msg = admin_create_model(c_m_nom, c_m_fournisseur, c_m_version, c_m_cout)
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()

    if is_super_admin and admin_tab is not None:
        with admin_tab:
            st.markdown("## Administration")
            st.write("Outils et indicateurs réservés au super admin.")
            admin_metrics_col1, admin_metrics_col2 = st.columns(2)
            admin_metrics_col1.metric("Exécutions chargées", len(df))
            admin_metrics_col1.metric("Modèles", df["modele_nom"].nunique())
            admin_metrics_col2.metric("Scénarios", df["nom_cas_usage"].nunique())
            admin_metrics_col2.metric(
                "Métriques RAGAS présentes",
                int(df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].count().sum()),
            )
            st.markdown("### Export complet des données")
            csv_all = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Télécharger toutes les exécutions (CSV)",
                data=csv_all,
                file_name="executions_all.csv",
                mime="text/csv",
            )

            st.divider()
            st.markdown("### Demandes d'accès en attente")
            
            pending = admin_list_pending_approvals()
            
            if pending:
                st.write(f"**{len(pending)} demande(s)** en attente de validation.")
                
                for user in pending:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 2])
                        
                        with col1:
                            st.markdown(f"**{user.nom_complet or user.email}**")
                            st.caption(f"Email: {user.email}")
                            st.caption(f"Département demandé: {user.departement}")
                            st.caption(f"Créé le: {user.date_creation.strftime('%d/%m/%Y %H:%M')}")
                        
                        with col2:
                            # Allow modifying department before approval
                            with engine.connect() as conn:
                                departments_result = conn.execute(text(
                                    "SELECT DISTINCT departement FROM scenarios ORDER BY departement"
                                )).fetchall()
                                departments = [row[0] for row in departments_result]
                            
                            final_dept = st.selectbox(
                                "Département final",
                                options=departments,
                                index=departments.index(user.departement) if user.departement in departments else 0,
                                key=f"dept_{user.id}"
                            )
                        
                        with col3:
                            if st.button("✅ Approuver", key=f"approve_{user.id}", use_container_width=True):
                                ok, msg = admin_approve_user(user.id, final_dept)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            
                            if st.button("❌ Refuser", key=f"reject_{user.id}", use_container_width=True):
                                ok, msg = admin_reject_user(user.id)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
            else:
                st.info("Aucune demande en attente.")
            
            st.divider()
            st.markdown("### Gestion des utilisateurs")
            st.write(
                "Les clients créent leur propre compte depuis l'écran de connexion. "
                "Les comptes Administrateur et Super Admin sont provisionnés ici."
            )

            users = admin_list_users()
            users_df = pd.DataFrame(
                [
                    {
                        "ID": u.id,
                        "Email": u.email,
                        "Rôle": ROLE_DISPLAY.get(u.role, u.role),
                        "Créé le": u.date_creation,
                    }
                    for u in users
                ]
            )
            if not users_df.empty:
                st.dataframe(users_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun utilisateur en base.")

            manage_col, create_col = st.columns(2)

            with manage_col:
                st.markdown("#### Modifier / supprimer un compte")
                if users:
                    user_labels = [f"{u.email} ({ROLE_DISPLAY.get(u.role, u.role)})" for u in users]
                    selected_idx = st.selectbox(
                        "Compte",
                        options=range(len(users)),
                        format_func=lambda i: user_labels[i],
                        key="admin_selected_user",
                    )
                    selected_user = users[selected_idx]

                    new_role_label = st.selectbox(
                        "Nouveau rôle",
                        options=[ROLE_DISPLAY[r] for r in ROLE_OPTIONS],
                        index=ROLE_OPTIONS.index(selected_user.role) if selected_user.role in ROLE_OPTIONS else 0,
                        key="admin_new_role",
                    )
                    if st.button("Mettre à jour le rôle", key="admin_update_role_btn"):
                        new_role = ROLE_OPTIONS[[ROLE_DISPLAY[r] for r in ROLE_OPTIONS].index(new_role_label)]
                        ok, msg = admin_update_role(selected_user.id, new_role)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()

                    with st.form("admin_reset_password_form"):
                        new_password = st.text_input("Nouveau mot de passe", type="password")
                        reset_submitted = st.form_submit_button("Réinitialiser le mot de passe")
                    if reset_submitted:
                        ok, msg = admin_reset_password(selected_user.id, new_password)
                        st.success(msg) if ok else st.error(msg)

                    if st.button("🗑️ Supprimer ce compte", key="admin_delete_user_btn"):
                        ok, msg = admin_delete_user(selected_user.id, requester_email=email)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            st.rerun()
                else:
                    st.info("Aucun compte à gérer pour le moment.")

            with create_col:
                st.markdown("#### Créer un nouveau compte")
                with st.form("admin_create_user_form"):
                    new_email = st.text_input("Adresse e-mail", key="admin_create_email")
                    new_password_create = st.text_input("Mot de passe", type="password", key="admin_create_password")
                    new_role_create_label = st.selectbox(
                        "Rôle",
                        options=[ROLE_DISPLAY[r] for r in ROLE_OPTIONS],
                        key="admin_create_role",
                    )
                    create_submitted = st.form_submit_button("Créer le compte")
                if create_submitted:
                    new_role_create = ROLE_OPTIONS[[ROLE_DISPLAY[r] for r in ROLE_OPTIONS].index(new_role_create_label)]
                    ok, msg = admin_create_user(new_email, new_password_create, new_role_create)
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()


if __name__ == "__main__":
    main()