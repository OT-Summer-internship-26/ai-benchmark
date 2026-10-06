"""
Secure Login Page with Email/Password Authentication
Replaces the open profile selection screen with secure authentication
"""
import streamlit as st
from src.auth.utils import login as auth_login
from src.dashboard.logo import LOGO_B64
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _inject_login_css():
    """Modern, secure login page styling"""
    st.markdown(
        """
        <style>
        /* Secure Login Page Styling */
        .secure-login-container {
            max-width: 420px;
            margin: 80px auto;
            padding: 40px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .secure-login-logo {
            text-align: center;
            margin-bottom: 32px;
        }
        
        .secure-login-logo img {
            width: 120px;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
        }
        
        .secure-login-title {
            text-align: center;
            color: white;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .secure-login-subtitle {
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            font-size: 14px;
            margin-bottom: 32px;
        }
        
        .secure-login-footer {
            text-align: center;
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.5);
            font-size: 12px;
        }
        
        .forgot-password-link {
            text-align: right;
            margin-top: 8px;
        }
        
        .forgot-password-link button {
            background: none !important;
            border: none !important;
            color: #4fc3f7 !important;
            text-decoration: underline;
            cursor: pointer;
            font-size: 13px;
            padding: 0 !important;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def secure_login_page():
    """
    Secure login page with email/password authentication.
    Replaces the open profile selection screen.
    """
    _inject_login_css()
    
    # Initialize session state
    st.session_state.setdefault("login_view", "signin")  # signin, forgot_password
    st.session_state.setdefault("login_error", None)
    st.session_state.setdefault("login_success_msg", None)
    
    # Main container
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # Logo
        st.markdown(
            f'<div class="secure-login-logo">'
            f'<img src="data:image/png;base64,{LOGO_B64}"></div>',
            unsafe_allow_html=True
        )
        
        # Title
        st.markdown('<div class="secure-login-title">Benchmark IA</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="secure-login-subtitle">Plateforme d\'évaluation des modèles IA · Ooredoo</div>',
            unsafe_allow_html=True
        )
        
        # Show success message if any
        if st.session_state.get("login_success_msg"):
            st.success(st.session_state["login_success_msg"])
            st.session_state["login_success_msg"] = None
        
        # Login or Forgot Password view
        if st.session_state["login_view"] == "signin":
            _render_signin_form()
        elif st.session_state["login_view"] == "forgot_password":
            _render_forgot_password_form()
        
        # Footer
        st.markdown(
            '<div class="secure-login-footer">© 2026 Ooredoo · Direction Innovation & IA</div>',
            unsafe_allow_html=True
        )


def _render_signin_form():
    """Render the sign-in form"""
    with st.form("secure_signin_form", clear_on_submit=False):
        email = st.text_input(
            "Adresse e-mail",
            placeholder="votre.email@ooredoo.tn",
            key="signin_email"
        )
        password = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="Votre mot de passe",
            key="signin_password"
        )
        
        submitted = st.form_submit_button("Se connecter →", use_container_width=True)
    
    # Forgot password link
    if st.button("Mot de passe oublié ?", key="forgot_pwd_btn", type="secondary"):
        st.session_state["login_view"] = "forgot_password"
        st.session_state["login_error"] = None
        st.rerun()
    
    # Process login
    if submitted:
        if not email or not password:
            st.error("⚠️ Veuillez renseigner votre e-mail et mot de passe.")
            return
        
        logger.info(f"Login attempt for email: {email}")
        
        # Call authentication function
        user, error_msg = auth_login(email, password)
        
        if user:
            # Login successful
            st.session_state["auth_user"] = user
            st.session_state["auth_email"] = user["email"]
            st.session_state["auth_role"] = user["role"]
            st.session_state["auth_user_id"] = user["id"]
            st.session_state["login_error"] = None
            
            logger.info(f"✅ Login successful: {email} (role: {user['role']})")
            
            st.success("✅ Connexion réussie ! Redirection...")
            import time
            time.sleep(0.8)
            st.rerun()
        else:
            # Login failed
            st.session_state["login_error"] = error_msg
            logger.warning(f"❌ Login failed for: {email} - {error_msg}")
    
    # Show error message if any
    if st.session_state.get("login_error"):
        st.error(f"🚫 {st.session_state['login_error']}")


def _render_forgot_password_form():
    """Render the forgot password form"""
    st.markdown("### 🔑 Réinitialiser le mot de passe")
    st.markdown(
        "Entrez votre adresse e-mail pour recevoir les instructions de réinitialisation.",
        help="Contactez votre administrateur système si vous ne recevez pas d'email."
    )
    
    with st.form("forgot_password_form"):
        email = st.text_input(
            "Adresse e-mail",
            placeholder="votre.email@ooredoo.tn",
            key="forgot_email"
        )
        
        submitted = st.form_submit_button("Envoyer les instructions", use_container_width=True)
    
    # Back to login
    if st.button("← Retour à la connexion", key="back_to_login"):
        st.session_state["login_view"] = "signin"
        st.session_state["login_error"] = None
        st.rerun()
    
    # Process password reset request
    if submitted:
        if not email:
            st.error("⚠️ Veuillez renseigner votre adresse e-mail.")
            return
        
        # TODO: Implement actual password reset logic
        # For now, show a message directing to admin
        st.info(
            f"📧 Si un compte existe pour **{email}**, vous recevrez un e-mail avec les "
            f"instructions de réinitialisation.\n\n"
            f"**Note:** Contactez votre administrateur système pour réinitialiser votre mot de passe."
        )
        
        logger.info(f"Password reset requested for: {email}")


def check_authentication() -> bool:
    """
    Check if user is authenticated.
    Returns True if authenticated, False otherwise.
    """
    return (
        st.session_state.get("auth_user") is not None
        and st.session_state.get("auth_email") is not None
        and st.session_state.get("auth_role") is not None
    )


def get_current_user() -> dict:
    """Get the current authenticated user"""
    return st.session_state.get("auth_user", {})


def logout():
    """Logout the current user"""
    user_email = st.session_state.get("auth_email", "unknown")
    
    # Clear all authentication-related session state
    keys_to_clear = [
        "auth_user",
        "auth_email",
        "auth_role",
        "auth_user_id",
        "login_error",
        "login_success_msg",
        "login_view"
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    logger.info(f"User logged out: {user_email}")
    st.rerun()


def require_role(allowed_roles: list[str]) -> bool:
    """
    Check if the current user has one of the allowed roles.
    Returns True if authorized, False otherwise.
    
    Args:
        allowed_roles: List of allowed roles (e.g., ["admin", "super_admin"])
    """
    current_role = st.session_state.get("auth_role")
    return current_role in allowed_roles


def show_unauthorized_message():
    """Show an unauthorized access message"""
    st.error("🚫 Accès refusé. Vous n'avez pas les permissions nécessaires pour accéder à cette fonctionnalité.")
    st.info("Cette fonctionnalité est réservée aux administrateurs. Contactez votre administrateur système si vous pensez avoir besoin d'un accès.")
