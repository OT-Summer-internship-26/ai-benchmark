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
from sqlalchemy import text, bindparam
from sqlalchemy.exc import IntegrityError
from src.dashboard.logo import LOGO_B64

from src.database.connection import engine

from src.database.connection import SessionLocal
from src.database.models import Utilisateur, Scenario, Modele
from src.auth.utils import verify_password, hash_password

# URL de base de l'API FastAPI (Sprint 3). Ajuste si elle tourne ailleurs
# (autre port, autre machine, etc.) — par exemple via une variable
# d'environnement si tu déploies un jour au-delà de ta machine locale.
API_BASE_URL = "http://localhost:8000"

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

def chart_caption(quoi: str, comment_lire: str, conclusion: str) -> None:
    """Affiche une légende pédagogique sous un graphique.
    À appeler juste après chaque st.vega_lite_chart / st.table / st.dataframe
    pour rendre le dashboard compréhensible même pour un public non-technique.
    """
    st.caption(
        f"📊 **Ce graphique montre** : {quoi}  \n"
        f"👀 **Comment le lire** : {comment_lire}  \n"
        f"✅ **À retenir** : {conclusion}"
    )


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
                ORDER BY e.date_execution DESC
                {limit_clause}
                """
            ),
            conn,
            params={"limit": limit} if limit is not None else {},
        )

        if executions.empty:
            return executions

        # Fetch only RAGAS criteria (0.0-1.0) to avoid mixing legacy heuristics.
        # NOTE: "IN :ids" needs an expanding bindparam with SQLAlchemy, otherwise
        # it can fail (or silently misbehave) depending on the DBAPI/driver.
        execution_ids = executions["execution_id"].tolist()
        scores_query = text(
            "SELECT execution_id, critere, note, commentaire "
            "FROM scores WHERE execution_id IN :ids "
            "AND (critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') "
            "OR (critere='score_global' AND note <= 1.0))"
        ).bindparams(bindparam("ids", expanding=True))

        scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})

    if scores.empty:
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
    df["score_global_auto"] = (
        df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]]
        .mean(axis=1)
        .round(3)
    )
    df["score_global_display"] = df["score_global_auto"]
    return df



@st.cache_data
def load_scenario_catalog() -> pd.DataFrame:
    """Charge tous les scénarios existants (avec ou sans exécutions), triés par département."""
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT departement, nom_cas_usage FROM scenarios ORDER BY departement, nom_cas_usage"),
            conn,
        )

def format_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "date_execution" in df.columns:
        df["date_execution"] = pd.to_datetime(df["date_execution"])
    return df


def build_metric_cards(df: pd.DataFrame, client_mode: bool = False) -> None:
    """Affiche les 4 cartes de métriques clés.
    En mode client (client_mode=True), le score brut (ex: 0.410) est
    remplacé par un label qualitatif (🟢/🟡/🔴) plus lisible pour un
    public non-technique — conformément à la demande de simplification.
    """
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Exécutions", len(df))
    col2.metric("Modèles", df["modele_nom"].nunique())
    col3.metric("Scénarios", df["nom_cas_usage"].nunique())
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
    chart_caption(
        quoi="le modèle IA le plus performant pour chaque département métier.",
        comment_lire="chaque ligne correspond à un département ; la colonne "
        "'Modèle recommandé' indique le modèle qui obtient le meilleur score sur ce département.",
        conclusion="c'est le modèle à privilégier si vous déployez une solution IA "
        "pour ce département spécifique.",
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

# Rappel visuel affiché comme placeholder du champ e-mail en mode démo.
# À retirer une fois que de vrais comptes existent.
DEMO_HINTS = {
    "client": "client@ooredoo.com",
    "admin": "admin@ooredoo.com",
    "super_admin": "superadmin@ooredoo.com",
}


def do_login(email: str, password: str, expected_role: str) -> bool:
    """
    Vérifie les identifiants en base. Retourne True en cas de succès.
    Vérifie aussi que le rôle réel du compte correspond au profil choisi
    dans le menu déroulant.
    """
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email.strip()).first()
    finally:
        db.close()

    if user is None or not verify_password(password.strip(), user.mot_de_passe_hash):
        st.session_state["login_error"] = "Identifiants invalides."
        return False

    if user.role != expected_role:
        st.session_state["login_error"] = (
            f"Ce compte est enregistré comme « {ROLE_DISPLAY.get(user.role, user.role)} », "
            f"pas « {ROLE_DISPLAY.get(expected_role, expected_role)} ». "
            "Choisissez le bon profil dans le menu."
        )
        return False

    st.session_state["login_error"] = None
    st.session_state["auth_email"] = user.email
    st.session_state["auth_role"] = ROLE_DISPLAY.get(user.role, user.role)

    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email.strip(), "password": password.strip()},
            timeout=10,
        )
        resp.raise_for_status()
        st.session_state["api_token"] = resp.json()["token"]
    except Exception:
        st.session_state["api_token"] = None  # pilotage indisponible si l'API est down

    return True
    


def do_signup(email: str, password: str, confirm_password: str) -> bool:
    """
    Crée un nouveau compte Utilisateur (toujours avec le rôle "client") et
    connecte la personne immédiatement après.

    Le libre-service de création de compte est volontairement limité au
    rôle client : les comptes admin / super_admin ne peuvent pas être
    auto-créés depuis cet écran, ils sont provisionnés par un super admin
    déjà connecté (voir gestion des utilisateurs dans l'onglet Administration).
    """
    email = email.strip()

    if not email or not password:
        st.session_state["login_error"] = "Merci de remplir tous les champs."
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
            mot_de_passe_hash=hash_password(password),
            role="client",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    st.session_state["login_error"] = None
    st.session_state["auth_email"] = email
    st.session_state["auth_role"] = ROLE_DISPLAY.get("client", "client")
    return True


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

def trigger_benchmark_run(
    scenario_ids: list[int] | None,
    model_names: list[str] | None,
    timeout: int = 900,
) -> tuple[bool, dict | str]:
    payload = {
        "scenario_ids": scenario_ids if scenario_ids else None,
        "model_names": model_names if model_names else None,
    }
    token = st.session_state.get("api_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        response = requests.post(
            f"{API_BASE_URL}/benchmark/run", json=payload, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.ConnectionError:
        return False, (
            f"Impossible de joindre l'API sur {API_BASE_URL}. Vérifie qu'elle tourne : "
            "`uvicorn src.api.main:app --reload --port 8000`"
        )
    except requests.exceptions.Timeout:
        return False, (
            "Le délai d'attente a été dépassé. Le benchmark est peut-être encore en cours "
            "côté serveur — vérifie les logs de l'API, puis rafraîchis le dashboard."
        )
    except requests.exceptions.HTTPError:
        return False, f"Erreur API ({response.status_code}) : {response.text}"
    except Exception as exc:
        return False, f"Erreur inattendue lors de l'appel à l'API : {exc}"


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
    """Compare le nombre de scénarios en base par département à la cible
    (16 par département). Utilisé dans l'onglet Administration pour
    garantir la complétude du catalogue."""
    scenarios = admin_list_scenarios()
    if not scenarios:
        return pd.DataFrame(columns=["Département", "Nb scénarios", "Statut"])

    counts: dict[str, int] = {}
    for s in scenarios:
        counts[s.departement] = counts.get(s.departement, 0) + 1

    rows = []
    for dep, count in sorted(counts.items()):
        statut = "✅ complet" if count >= SCENARIOS_CIBLE_PAR_DEPARTEMENT else f"❌ manque {SCENARIOS_CIBLE_PAR_DEPARTEMENT - count}"
        rows.append({"Département": dep, "Nb scénarios": count, "Statut": statut})

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


ROLE_ICONS = {
    "client": "👤",
    "admin": "🛠️",
    "super_admin": "🔐",
}

ROLE_TAGLINES = {
    "client": "Consultez les indicateurs clés du benchmark.",
    "admin": "Analysez, exportez et pilotez les résultats.",
    "super_admin": "Accès complet, y compris les outils d'administration.",
}


def _inject_login_css() -> None:
    st.markdown(
        """
        <style>
        header {visibility:hidden;}
        #MainMenu {visibility:hidden;}
        footer {visibility:hidden;}
        section[data-testid="stSidebar"] { display: none; }

        div[data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 15% 12%, rgba(255,255,255,0.10), transparent 45%),
                radial-gradient(circle at 85% 88%, rgba(0,0,0,0.25), transparent 55%),
                linear-gradient(155deg, #F2323D 0%, #ED1C29 30%, #B4121C 68%, #6E0A10 100%);
            background-attachment: fixed;
        }
        div[data-testid="stMain"] { display:flex; }
        div.block-container {
            min-height: 100vh;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            padding: 4vh 3rem !important;
            max-width: 1080px !important;
            margin: 0 auto;
        }

        /* Logo + heading */
        .oi-logo-wrap {
            position: relative;
            display:flex; justify-content:center; align-items:center;
            margin-bottom: 38px;
        }
        .oi-logo-wrap::before {
            content: "";
            position: absolute;
            width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(255,255,255,0.38) 0%, rgba(255,255,255,0.08) 55%, transparent 75%);
            filter: blur(6px);
            z-index: 0;
        }
        .oi-logo-wrap img {
            position: relative;
            z-index: 1;
            width: 230px;
            padding: 38px;
            background: white;
            border-radius: 40px;
            box-shadow:
                0 30px 70px rgba(0,0,0,0.38),
                0 0 0 8px rgba(255,255,255,0.10);
        }
        .oi-eyebrow {
            text-align:center; color: rgba(255,255,255,0.78); font-size: 15px;
            letter-spacing: 4px; text-transform: uppercase; font-weight: 700; margin-bottom: 14px;
        }
        .oi-title {
            text-align:center; color:white; font-weight: 800; font-size: 64px;
            line-height: 1.12; letter-spacing: -1px;
        }
        .oi-title.oi-title-sub { font-size: 42px; }
        .oi-subtitle {
            text-align:center; color: rgba(255,255,255,0.85); font-size: 20px;
            max-width: 620px; margin: 20px auto 0 auto; line-height: 1.6;
        }

        /* Generic glass card used for the CTA / role tiles / auth card */
        .st-key-oi_cta button,
        div[class*="st-key-oi_role_card_"] button,
        .st-key-oi_back button {
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.28) !important;
            color: white !important;
            backdrop-filter: blur(6px);
        }
        .st-key-oi_cta { max-width: 460px; margin: 0 auto; }
        .st-key-oi_cta button {
            border-radius: 999px !important;
            padding: 20px 10px !important;
            font-weight: 700 !important;
            font-size: 19px !important;
            background: white !important;
            color: #B4121C !important;
            border: none !important;
            box-shadow: 0 16px 36px rgba(0,0,0,0.28);
            transition: transform .15s ease;
        }
        .st-key-oi_cta button:hover { transform: translateY(-2px); background:#fff !important; }
        .st-key-oi_cta button p { font-size: 19px !important; }

        div[class*="st-key-oi_role_card_"] button {
            border-radius: 22px !important;
            padding: 38px 26px !important;
            min-height: 240px;
            white-space: pre-wrap;
            text-align: left !important;
            font-weight: 600 !important;
            font-size: 17px !important;
            line-height: 1.5 !important;
            transition: transform .15s ease, background .15s ease;
        }
        div[class*="st-key-oi_role_card_"] button p { font-size: 17px !important; line-height: 1.5 !important; }
        div[class*="st-key-oi_role_card_"] button:hover {
            background: rgba(255,255,255,0.20) !important;
            border-color: rgba(255,255,255,0.5) !important;
            transform: translateY(-4px);
        }

        .st-key-oi_back { max-width: 160px; margin-bottom: 18px; }
        .st-key-oi_back button {
            border-radius: 999px !important;
            padding: 6px 18px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }

        /* Auth card */
        .st-key-oi_auth_card {
            background: rgba(255,255,255,0.98);
            border-radius: 26px;
            padding: 48px 52px 34px 52px;
            box-shadow: 0 26px 64px rgba(0,0,0,0.32);
            margin-top: 10px;
            max-width: 520px;
            margin-left: auto;
            margin-right: auto;
        }
        .oi-role-chip {
            display:inline-flex; align-items:center; gap:6px;
            background:#FDECEC; color:#B4121C; font-weight:700; font-size:13px;
            letter-spacing: 0.5px; padding: 7px 16px; border-radius: 999px; margin-bottom: 16px;
        }
        .oi-auth-heading { font-weight: 800; font-size: 28px; color:#1a1a1a; margin-bottom: 4px; }
        .oi-auth-caption { color:#8A93A8; font-size: 15px; margin-bottom: 22px; }

        .st-key-oi_auth_card div[role="radiogroup"] {
            background:#F3F4F7; padding: 4px; border-radius: 12px; gap: 0 !important;
        }
        .st-key-oi_auth_card div[role="radiogroup"] label {
            flex:1; justify-content:center; padding: 9px 0; border-radius: 9px; margin:0 !important;
        }
        .st-key-oi_auth_card div[data-testid="stForm"] button {
            background: #ED1C29; color: white; font-weight: 700; border: none;
            border-radius: 10px; padding: 13px 0; margin-top: 12px; font-size: 16px;
        }
        .st-key-oi_auth_card div[data-testid="stForm"] button:hover { background: #C8161F; }

        @media (max-width: 900px) {
            .oi-title { font-size: 42px; }
            .st-key-oi_auth_card { padding: 34px 26px 24px 26px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def login_page():
    """Écran de connexion plein écran, en un seul flux progressif :
    accueil → choix du profil → connexion / création de compte.
    """
    _inject_login_css()

    st.session_state.setdefault("login_stage", "landing")
    st.session_state.setdefault("login_mode", "signin")
    st.session_state.setdefault("login_role", None)

    st.markdown('<div class="oi-logo-wrap">'
                f'<img src="data:image/png;base64,{LOGO_B64}"></div>', unsafe_allow_html=True)

    stage = st.session_state["login_stage"]

    # -------------------------------------------------------------- landing
    if stage == "landing":
        st.markdown('<div class="oi-eyebrow">Ooredoo · Direction IA</div>', unsafe_allow_html=True)
        st.markdown('<div class="oi-title">Benchmark IA</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="oi-subtitle">Évaluez, comparez et pilotez la performance des '
            "modèles IA déployés au sein d'Ooredoo, sur des cas d'usage métier réels.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:34px;'></div>", unsafe_allow_html=True)

        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            with st.container(key="oi_cta"):
                if st.button("Accéder à la plateforme  →", use_container_width=True):
                    st.session_state["login_stage"] = "role"
                    st.rerun()

    # ----------------------------------------------------------------- role
    elif stage == "role":
        with st.container(key="oi_back"):
            if st.button("← Retour", key="oi_back_role"):
                st.session_state["login_stage"] = "landing"
                st.rerun()

        st.markdown('<div class="oi-eyebrow">Étape 1 / 2</div>', unsafe_allow_html=True)
        st.markdown('<div class="oi-title oi-title-sub">Choisissez votre profil</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="oi-subtitle">L\'affichage et les données disponibles s\'adaptent '
            "au profil sélectionné.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:36px;'></div>", unsafe_allow_html=True)

        cols = st.columns(3, gap="medium")
        for col, role_key in zip(cols, ROLE_OPTIONS):
            with col:
                with st.container(key=f"oi_role_card_{role_key}"):
                    label = f"{ROLE_ICONS[role_key]}\n\n**{ROLE_DISPLAY[role_key]}**\n\n{ROLE_TAGLINES[role_key]}"
                    if st.button(label, key=f"role_btn_{role_key}", use_container_width=True):
                        st.session_state["login_role"] = role_key
                        st.session_state["login_stage"] = "auth"
                        st.session_state["login_mode"] = "signin"
                        st.rerun()

    # ----------------------------------------------------------------- auth
    elif stage == "auth":
        role_key = st.session_state["login_role"] or "client"

        with st.container(key="oi_back"):
            if st.button("← Changer de profil", key="oi_back_auth"):
                st.session_state["login_stage"] = "role"
                st.rerun()

        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            with st.container(key="oi_auth_card"):
                st.markdown(
                    f'<div class="oi-role-chip">{ROLE_ICONS[role_key]} {ROLE_DISPLAY[role_key]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="oi-auth-heading">Accès à la plateforme</div>', unsafe_allow_html=True)

                can_self_signup = role_key == "client"

                if can_self_signup:
                    st.markdown('<div class="oi-auth-caption">Connectez-vous ou créez un compte pour continuer</div>', unsafe_allow_html=True)
                    mode_label = st.radio(
                        "Action",
                        options=["Se connecter", "Créer un compte"],
                        horizontal=True,
                        index=0 if st.session_state["login_mode"] == "signin" else 1,
                        label_visibility="collapsed",
                    )
                    st.session_state["login_mode"] = "signin" if mode_label == "Se connecter" else "signup"
                else:
                    st.markdown(
                        '<div class="oi-auth-caption">Les comptes Administrateur et Super Admin sont créés '
                        "par un super admin déjà connecté, depuis l'onglet Administration.</div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state["login_mode"] = "signin"

                st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

                if st.session_state["login_mode"] == "signin":
                    with st.form("signin_form"):
                        email = st.text_input(
                            "Adresse e-mail",
                            placeholder="vous@exemple.com" if can_self_signup else DEMO_HINTS.get(role_key, ""),
                        )
                        password = st.text_input("Mot de passe", type="password")
                        submitted = st.form_submit_button("Se connecter", use_container_width=True)
                    if submitted and do_login(email, password, expected_role=role_key):
                        st.rerun()
                else:
                    with st.form("signup_form"):
                        email = st.text_input("Adresse e-mail")
                        password = st.text_input("Mot de passe", type="password")
                        confirm = st.text_input("Confirmer le mot de passe", type="password")
                        submitted = st.form_submit_button("Créer un compte", use_container_width=True)
                    if submitted and do_signup(email, password, confirm):
                        st.rerun()

                if st.session_state.get("login_error"):
                    st.error(st.session_state["login_error"])


def render_sidebar_identity(email: str, role: str) -> None:
    with st.sidebar.container(key="brand_header"):
        st.markdown(
            f"<div style='text-align:center; padding:14px 0 10px 0;'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' style='width:96px;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style='text-align:center; color:white; padding-bottom:14px;'>
                <div style='font-weight:700; font-size:14px; margin-top:2px;'>{email}</div>
                <div style='font-size:11px; letter-spacing:1px; opacity:0.85; margin-top:2px;'>
                    {role.upper()}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <style>
        .st-key-brand_header {
            background: linear-gradient(165deg, #ED1C29 0%, #A80F17 100%);
            border-radius: 0 0 16px 16px;
            margin: -1rem -1rem 0.8rem -1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("Se déconnecter", use_container_width=True):
        st.session_state.pop("auth_email", None)
        st.session_state.pop("auth_role", None)
        st.session_state.pop("login_mode", None)
        st.session_state.pop("login_role", None)
        st.session_state.pop("login_stage", None)
        st.rerun()

    role_messages = {
        "Utilisateur": "Vue simplifiée : indicateurs clés uniquement.",
        "Administrateur": "Accès complet aux données métier et aux exports.",
        "Super Admin": "Accès complet + outils d'administration.",
    }
    st.sidebar.caption(role_messages.get(role, ""))
    st.sidebar.divider()

# ---------------------------------------------------------------------------
# Main app (post-login)
# ---------------------------------------------------------------------------

def main() -> None:
    if "auth_role" not in st.session_state:
        login_page()
        st.stop()

    email = st.session_state["auth_email"]
    role = st.session_state["auth_role"]
    is_admin = role in ["Administrateur", "Super Admin"]
    is_super_admin = role == "Super Admin"
    is_client = role == "Utilisateur"

    render_sidebar_identity(email, role)

    st.markdown(
        """
        <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:6px;">
            <span style="font-family:'Trebuchet MS',sans-serif; font-weight:800; font-size:26px; color:#ED1C29;">ooredoo</span>
            <span style="font-size:22px; color:#1a1a1a; font-weight:600;">Benchmark IA</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "Ce dashboard permet de comparer les résultats de benchmark RAG + LLM, "
        "d'analyser la performance des modèles et de consulter les exécutions détaillées."
    )

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

    df = load_executions(limit=limit)
    
    df = format_datetime(df)

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

    if is_admin and legacy_count and legacy_count > 0:
        st.sidebar.warning(
            f"Attention — {legacy_count} scores heuristiques anciens détectés en base.\n"
            "Ces anciennes métriques peuvent fausser les agrégations. Exécutez `python scripts/cleanup_scores.py --dry-run` puis `--apply` pour nettoyer."
        )

    if df.empty:
        st.warning("Aucune exécution disponible dans la base de données.")
        return

    if is_admin:
        modeles = df["modele_nom"].unique().tolist()

        scenario_catalog = load_scenario_catalog()
        scenarios = scenario_catalog["nom_cas_usage"].tolist()
        departement_par_scenario = dict(zip(scenario_catalog["nom_cas_usage"], scenario_catalog["departement"]))

        selected_modeles = st.sidebar.multiselect("Modèles", modeles, default=modeles)
        selected_scenarios = st.sidebar.multiselect(
           "Scénarios",
          scenarios,
          default=scenarios,
          format_func=lambda nom: f"{nom} ({departement_par_scenario.get(nom, '?')})",
    )
  
        min_date = df["date_execution"].min().date()
        max_date = df["date_execution"].max().date()
        date_range = st.sidebar.date_input(
           "Période d'exécution",
          value=(min_date, max_date),
          min_value=min_date,
          max_value=max_date,
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
        if role == "Utilisateur":
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
                chart_caption(
                    quoi="les 3 modèles IA les plus performants, tous départements confondus.",
                    comment_lire="le classement va du plus performant (ligne 1) au moins performant (ligne 3) ; "
                    "la colonne 'Qualité' résume le niveau de performance avec un code couleur.",
                    conclusion="privilégiez le modèle en tête de liste pour vos besoins IA généraux.",
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
                chart_caption(
                    quoi="les 3 cas d'usage métier où l'IA obtient les meilleurs résultats.",
                    comment_lire="chaque ligne est un scénario métier, classé du plus réussi au moins réussi.",
                    conclusion="ce sont les cas d'usage à déployer en priorité, l'IA y est la plus fiable.",
                )
            else:
                st.info("Pas de scénarios à afficher pour le Top 3.")

            st.divider()
            build_client_department_comparison(filtered)
        else:
            build_metric_cards(filtered, client_mode=False)
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
                        "mark": {"type": "line", "point": True},
                        "encoding": {
                            "x": {"field": "date_execution", "type": "temporal", "title": "Date"},
                            "y": {"field": "score_global_display", "type": "quantitative", "title": "Score moyen"},
                        },
                    },
                    use_container_width=True,
                )
                chart_caption(
                    quoi="l'évolution du score global moyen (toutes exécutions) au fil des jours.",
                    comment_lire="l'axe horizontal est la date, l'axe vertical le score moyen (0 à 1) ; "
                    "une courbe qui monte signifie une amélioration globale de la qualité des réponses IA.",
                    conclusion="une tendance stable ou croissante est bon signe ; une chute soudaine "
                    "mérite d'être investiguée (changement de modèle, panne RAG, etc.).",
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
                top3["score_global_display"] = top3["score_global_display"].map(lambda v: f"{v:.3f}")
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
                best_per_scenario["score_global_display"] = best_per_scenario["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(best_per_scenario.rename(columns={"nom_cas_usage": "Scénario", "modele_nom": "Meilleur modèle", "score_global_display": "Score"}))
                chart_caption(
                    quoi="pour chaque scénario métier, le modèle qui obtient le meilleur score.",
                    comment_lire="chaque ligne = un scénario ; la colonne 'Meilleur modèle' indique quel "
                    "modèle choisir spécifiquement pour ce cas d'usage.",
                    conclusion="utile pour affiner le choix de modèle scénario par scénario plutôt que "
                    "d'utiliser un seul modèle partout.",
                )
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
                chart_caption(
                    quoi="la contribution de chaque critère RAGAS (fidélité, pertinence, précision, "
                    "rappel du contexte) au score de chaque modèle.",
                    comment_lire="chaque barre horizontale représente un modèle, divisée en segments colorés "
                    "(un par critère) ; plus la barre est longue, meilleur est le modèle globalement.",
                    conclusion="privilégiez le modèle avec la barre la plus longue ET la plus équilibrée "
                    "entre les couleurs (pas de segment anormalement petit).",
                )
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
                chart_caption(
                    quoi="le score global obtenu par chaque combinaison modèle × scénario.",
                    comment_lire="chaque case croise un modèle (colonne) et un scénario (ligne) ; "
                    "plus la couleur est foncée/intense, meilleur est le score à cet endroit.",
                    conclusion="repérez les zones claires (score faible) : ce sont les combinaisons "
                    "modèle/scénario à éviter ou à améliorer en priorité.",
                )
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
            chart_caption(
                quoi="à gauche, la répartition des exécutions par tranche de score ; à droite, par tranche de latence (temps de réponse).",
                comment_lire="chaque barre montre combien d'exécutions tombent dans une tranche donnée ; "
                "une distribution concentrée à droite pour le score = bon signe, une distribution concentrée "
                "à gauche pour la latence = réponses rapides.",
                conclusion="un pic de score autour de valeurs basses ou un pic de latence à droite (lent) "
                "signale un problème à investiguer.",
            )
            st.divider()

    with scenarios_tab:

        if role == "Utilisateur":
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
            chart_caption(
                quoi="les 5 cas d'usage métier les plus performants avec l'IA actuellement testée.",
                comment_lire="chaque ligne est un scénario, avec un niveau de qualité résumé par un code couleur.",
                conclusion="ce sont les cas d'usage à privilégier pour un déploiement IA immédiat.",
            )
        else:
            st.markdown("## Comparaison des scénarios")
            st.write("Comparez les scénarios par score global, métriques dimensions et pertinence.")
            st.dataframe(summary_scenario, use_container_width=True)
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
            chart_caption(
                quoi="le classement des 5 meilleurs scénarios par score global moyen.",
                comment_lire="chaque barre horizontale représente un scénario ; plus la barre est longue, "
                "meilleur est le score obtenu par l'IA sur ce cas d'usage.",
                conclusion="les scénarios en haut du classement sont les plus fiables pour un déploiement.",
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
                        "x": {"field": "Note", "type": "quantitative"},
                        "y": {"field": "Scénario", "type": "nominal", "sort": "-x"},
                        "color": {"field": "Critère", "type": "nominal"},
                        "tooltip": [
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative"},
                        ],
                    },
                },
                use_container_width=True,
            )
            chart_caption(
                quoi="le détail des 4 critères RAGAS (fidélité, pertinence, précision, rappel) pour chaque scénario.",
                comment_lire="chaque scénario a 4 barres colorées, une par critère ; comparez les couleurs "
                "entre scénarios pour voir où l'IA excelle ou faiblit.",
                conclusion="un scénario avec un critère systématiquement faible (ex: fidélité) indique "
                "un problème spécifique à corriger (souvent le contexte RAG fourni).",
            )
            st.divider()
            st.markdown("### Top 3 scénarios")
            st.table(summary_scenario.head(3).rename(
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
        if role == "Utilisateur":
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
            chart_caption(
                quoi="l'ensemble des modèles IA testés, classés avec un niveau de qualité et leur vitesse de réponse.",
                comment_lire="chaque ligne est un modèle ; la couleur indique le niveau de qualité, "
                "la latence indique le temps de réponse moyen.",
                conclusion="pour un besoin où la rapidité compte, privilégiez un modèle 🟢 avec une faible latence.",
            )
        else:
            st.markdown("## Comparaison modèles")
            st.write("Comparez les modèles par score global, métriques RAGAS, et latence.")
            st.dataframe(summary_model, use_container_width=True)
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
            chart_caption(
                quoi="le détail des 4 critères RAGAS pour chaque modèle testé.",
                comment_lire="chaque modèle a 4 valeurs (une par critère) ; comparez les longueurs de "
                "barres entre modèles pour voir lequel excelle sur quel critère.",
                conclusion="un modèle globalement fort mais faible sur un seul critère peut suffire "
                "selon vos priorités métier (ex: la vitesse compte plus que la précision).",
            )
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
                chart_caption(
                    quoi="la dispersion des scores obtenus par chaque modèle (pas seulement la moyenne).",
                    comment_lire="la boîte représente la majorité des scores obtenus ; plus la boîte est "
                    "petite et haute, plus le modèle est constant et performant. Les points isolés sont "
                    "des cas exceptionnels (très bons ou très mauvais).",
                    conclusion="préférez un modèle avec une boîte compacte et haute : il est fiable "
                    "et prévisible, pas seulement bon en moyenne.",
                )
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
                chart_caption(
                    quoi="l'évolution du score des 3 meilleurs modèles au fil du temps.",
                    comment_lire="chaque courbe colorée est un modèle ; suivez sa tendance dans le temps.",
                    conclusion="une courbe stable en haut du graphique = modèle fiable dans la durée ; "
                    "une courbe qui descend mérite une réévaluation.",
                )
            else:
                st.info("Pas de séries temporelles disponibles pour les scores.")

            st.divider()
            st.markdown("### Top 5 modèles — résumé")
            top5 = summary_model.head(5).copy()
            if not top5.empty:
                top5["score_global_display"] = top5["score_global_display"].map(lambda v: f"{v:.3f}")
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
            st.dataframe(
                filtered[display_columns]
                .sort_values("date_execution", ascending=False)
                .rename(
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

            selected_execution = st.selectbox(
                "Sélectionner une exécution",
                filtered["execution_id"].astype(str).tolist(),
            )
            execution_data = filtered[filtered["execution_id"] == int(selected_execution)].iloc[0]

            st.divider()
            st.markdown("### Exécution sélectionnée")
            left_col, right_col = st.columns(2)
            left_col.markdown(
                f"**Modèle** : {execution_data['modele_nom']}  \n"
                f"**Scénario** : {execution_data['nom_cas_usage']}  \n"
                f"**Département** : {execution_data['departement']}"
            )
            right_col.markdown(
                f"**Score global** : {execution_data['score_global_auto']}  \n"
                f"**Latence** : {execution_data['latence_secondes']:.2f}s  \n"
                f"**Coût estimé** : {execution_data['cout_estime']}"
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
            for label, value in score_items.items():
                st.write(f"- **{label}** : {value}")

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
                "Appelle POST /benchmark/run sur l'API FastAPI (Sprint 3). "
                "Laisse un champ vide pour utiliser la valeur par défaut de l'API "
                "(tous les scénarios / tous les modèles Ollama installés)."
            )

            all_scenarios = admin_list_scenarios()
            scenario_options = {s.id: f"{s.nom_cas_usage} ({s.departement})" for s in all_scenarios}
            selected_scenario_ids = st.multiselect(
                "Scénarios à exécuter",
                options=list(scenario_options.keys()),
                format_func=lambda sid: scenario_options[sid],
                key="run_scenario_ids",
            )

            model_names_raw = st.text_input(
                "Modèles à tester (noms séparés par des virgules, ex : llama3.1:8b, mistral:7b)",
                key="run_model_names",
                help="Ce champ attend les identifiants de modèles Ollama tels qu'utilisés par le pipeline "
                "(pas forcément identiques aux noms affichés dans le catalogue ci-dessous).",
            )
            model_names_list = [m.strip() for m in model_names_raw.split(",") if m.strip()] or None

            if st.button("🚀 Lancer le benchmark", key="run_benchmark_btn"):
                with st.spinner("Exécution du benchmark en cours — cela peut prendre plusieurs minutes…"):
                    ok, result = trigger_benchmark_run(
                        scenario_ids=selected_scenario_ids or None,
                        model_names=model_names_list,
                    )
                if ok:
                    st.success(f"Benchmark terminé — statut : {result.get('status', 'inconnu')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Scénarios exécutés", result.get("nb_scenarios", 0))
                    m2.metric("Modèles testés", result.get("nb_modeles", 0))
                    m3.metric("Exécutions produites", result.get("nb_executions", 0))
                    if result.get("erreurs"):
                        st.warning("Erreurs rencontrées pendant l'exécution :")
                        for err in result["erreurs"]:
                            st.write(f"- {err}")
                    if result.get("rapport"):
                        with st.expander("Rapport détaillé (JSON)"):
                            st.json(result["rapport"])
                    st.info("Vide le cache pour voir les nouvelles exécutions dans les autres onglets.")
                    if st.button("🔄 Rafraîchir les données du dashboard", key="refresh_after_run"):
                        st.cache_data.clear()
                        st.rerun()
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
                st.table(completeness_df)
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