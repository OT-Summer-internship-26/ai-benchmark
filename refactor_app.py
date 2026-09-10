#!/usr/bin/env python3
"""
Systematically refactor src/dashboard/app.py for UI/UX redesign
Only changes: tabs → radio, sidebar reorganization, logo improvement
"""

import re

# Read the original file
with open('src/dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Add new functions before render_sidebar_identity
new_functions = '''def render_sidebar_header() -> None:
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

# Find where to insert the new functions
insert_marker = 'def render_sidebar_identity(email: str, role: str) -> None:'
content = content.replace(
    insert_marker,
    new_functions + insert_marker.replace('render_sidebar_identity', 'render_sidebar_identity\n    """DEPRECATED: Use render_sidebar_header() + render_sidebar_account() instead."""')
)

# Save the modified content
with open('src/dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Step 1: Added new functions")
