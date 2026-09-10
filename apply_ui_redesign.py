#!/usr/bin/env python3
"""
Apply UI/UX redesign to src/dashboard/app.py
This script handles all refactoring in a safe, controlled manner
"""
import re

# Read original
with open('src/dashboard/app.py', 'r', encoding='utf-8') as f:
    original = f.read()

# Step 1: Insert new functions before render_sidebar_identity
new_funcs = '''def render_sidebar_header() -> None:
    """Render improved logo header at TOP of sidebar with proper centering, aspect ratio, and spacing."""
    st.markdown(
        f"""
        <div style='
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 16px 0 12px 0;
            margin-bottom: 8px;
        '>
            <img 
                src='data:image/png;base64,{LOGO_B64}' 
                style='
                    max-width: 140px;
                    height: auto;
                    display: block;
                    object-fit: contain;
                '
                alt='Ooredoo Logo'
            >
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='margin: 8px 0; opacity: 0.3;'>", unsafe_allow_html=True)


def render_sidebar_account(email: str, role: str) -> None:
    """Render the account/identity section at the BOTTOM of sidebar."""
    st.sidebar.divider()
    
    st.sidebar.markdown(
        f"""
        <div style='text-align:center; color:white; padding:12px 0;'>
            <div style='font-weight:700; font-size:14px; margin-bottom:4px;'>{email}</div>
            <div style='font-size:11px; letter-spacing:1px; opacity:0.85; margin-bottom:12px;'>
                {role.upper()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.pop("auth_email", None)
        st.session_state.pop("auth_role", None)
        st.session_state.pop("login_mode", None)
        st.session_state.pop("login_role", None)
        st.session_state.pop("login_stage", None)
        st.rerun()

    role_messages = {
        "Client": "Vue simplifiée : indicateurs clés uniquement.",
        "Admin": "Accès complet aux données métier et aux exports.",
        "Super Admin": "Accès complet + outils d'administration.",
    }
    st.sidebar.caption(role_messages.get(role, ""))


'''

original = original.replace(
    'def render_sidebar_identity(email: str, role: str) -> None:',
    new_funcs + 'def render_sidebar_identity(email: str, role: str) -> None:\n    """DEPRECATED: Use render_sidebar_header() + render_sidebar_account() instead."""'
)

# Step 2: Keep render_sidebar_identity for now (it's for backward compat)

# Step 3: Replace tabs creation with conditional
original = re.sub(
    r'tabs = \["Vue d\'ensemble".*?admin_tab = extra_tabs\.pop\(0\) if is_super_admin else None\n\n    with overview_tab:',
    'if selected_nav == "📊 Vue d\'ensemble":',
    original,
    flags=re.DOTALL,
    count=1
)

# Step 4: Replace scenario tab
original = original.replace(
    '    with scenarios_tab:\n\n        if role == "Client":',
    '    elif selected_nav == "📋 Comparaison scénarios":\n\n        if role == "Client":'
)

# Step 5: Replace models tab
original = original.replace(
    '    with models_tab:\n        if role == "Client":',
    '    elif selected_nav == "📈 Comparaison modèles":\n        if role == "Client":'
)

# Step 6: Replace details tab  (more complex due to the nested structure)
original = original.replace(
    '        with details_tab:',
    '    elif selected_nav == "🔍 Détails des exécutions":'
)

# Step 7: Replace pilotage
original = original.replace(
    '    if is_admin and pilotage_tab is not None:\n        with pilotage_tab:',
    '    elif selected_nav == "🎛️ Pilotage":'
)

# Step 8: Replace admin
original = original.replace(
    '    if is_super_admin and admin_tab is not None:\n        with admin_tab:',
    '    elif selected_nav == "⚙️ Administration":'
)

# Save
with open('src/dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(original)

print("✅ Applied UI redesign transformations")
