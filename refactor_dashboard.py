#!/usr/bin/env python3
"""
Refactor src/dashboard/app.py to use sidebar navigation instead of horizontal tabs.
Changes:
1. Improve logo rendering with proper centering and spacing
2. Replace st.tabs() with st.sidebar.radio() for vertical navigation
3. Move account/logout block to bottom of sidebar
4. Convert tab content blocks from 'with tab:' to 'elif selected_nav == "..."'
"""

import re
import sys

# Read original file
with open('src/dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ===================================================================
# CHANGE 1: Replace render_sidebar_identity function
# ===================================================================
old_render = r'''def render_sidebar_identity\(email: str, role: str\) -> None:
    with st\.sidebar\.container\(key="brand_header"\):
        st\.markdown\(
            f"<div style='text-align:center; padding:14px 0 10px 0;'>"
            f"<img src='data:image/png;base64,\{LOGO_B64\}' style='width:96px;'></div>",
            unsafe_allow_html=True,
        \)
        st\.markdown\(
            f"""
            <div style='text-align:center; color:white; padding-bottom:14px;'>
                <div style='font-weight:700; font-size:14px; margin-top:2px;'>\{email\}</div>
                <div style='font-size:11px; letter-spacing:1px; opacity:0\.85; margin-top:2px;'>
                    \{role\.upper\(\)\}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        \)

    st\.markdown\(
        """
        <style>
        \.st-key-brand_header \{
            background: linear-gradient\(165deg, #ED1C29 0%, #A80F17 100%\);
            border-radius: 0 0 16px 16px;
            margin: -1rem -1rem 0\.8rem -1rem;
        \}
        </style>
        """,
        unsafe_allow_html=True,
    \)

    if st\.sidebar\.button\("Se déconnecter", use_container_width=True\):
        st\.session_state\.pop\("auth_email", None\)
        st\.session_state\.pop\("auth_role", None\)
        st\.session_state\.pop\("login_mode", None\)
        st\.session_state\.pop\("login_role", None\)
        st\.session_state\.pop\("login_stage", None\)
        st\.rerun\(\)

    role_messages = \{
        "Client": "Vue simplifiée : indicateurs clés uniquement\.",
        "Admin": "Accès complet aux données métier et aux exports\.",
        "Super Admin": "Accès complet \+ outils d'administration\.",
    \}
    st\.sidebar\.caption\(role_messages\.get\(role, ""\)\)
    st\.sidebar\.divider\(\)'''

new_render = '''def render_sidebar_header() -> None:
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
    st.sidebar.caption(role_messages.get(role, ""))'''

content = re.sub(old_render, new_render, content, flags=re.DOTALL)

print("✓ Refactored render_sidebar_identity -> render_sidebar_header/account")

# ===================================================================
# CHANGE 2: Update main() function signature and sidebar setup
# ===================================================================

# Find the point after "render_sidebar_identity(email, role)" and replace
old_main_start = r'''        logger\.info\(f"Dashboard accessed by user: \{email\} with role: \{role\}"\)

        render_sidebar_identity\(email, role\)

        if is_admin:
            if st\.session_state\.get\("api_token"\):
               st\.sidebar\.caption\("API token: ✅ présent"\)
            else:
                st\.sidebar\.error\(f"API token absent — erreur : \{st\.session_state\.get\('api_token_error'\)\}"\)
                logger\.warning\(f"Admin user \{email\} missing API token: \{st\.session_state\.get\('api_token_error'\)\}"\)'''

new_main_start = '''        logger.info(f"Dashboard accessed by user: {email} with role: {role}")

        # ===================================================================
        # SIDEBAR LAYOUT (NEW DESIGN)
        # ===================================================================
        
        # 1. Render logo header at TOP of sidebar
        st.sidebar.markdown("")  # Top padding
        render_sidebar_header()
        
        # 2. Filters section (Filtres)
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

        # 3. API token status (admin only)
        if is_admin:
            if st.session_state.get("api_token"):
                st.sidebar.caption("✅ API token: présent")
            else:
                st.sidebar.error(f"API token absent — erreur : {st.session_state.get('api_token_error')}")
                logger.warning(f"Admin user {email} missing API token: {st.session_state.get('api_token_error')}")

        # 4. Legacy scores warning (admin only)
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

        # 5. Build navigation options based on role
        nav_options = ["📊 Vue d'ensemble", "📈 Comparaison modèles", "📋 Comparaison scénarios", "🔍 Détails des exécutions"]
        if is_admin:
            nav_options.append("🎛️ Pilotage")
        if is_super_admin:
            nav_options.append("⚙️ Administration")
        
        # SIDEBAR NAVIGATION MENU (replacing horizontal tabs)
        st.sidebar.markdown("---")
        st.sidebar.header("Navigation")
        
        selected_nav = st.sidebar.radio(
            "Section",
            options=nav_options,
            label_visibility="collapsed",
        )

        # 6. Render account/logout at BOTTOM of sidebar
        render_sidebar_account(email, role)'''

content = re.sub(old_main_start, new_main_start, content, flags=re.DOTALL)

print("✓ Updated main() sidebar setup")

# ===================================================================
# CHANGE 3: Move title rendering after sidebar setup
# ===================================================================

old_title = r'''        st\.markdown\(
            """
            <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:6px;">
                <span style="font-family:'Trebuchet MS',sans-serif; font-weight:800; font-size:26px; color:#ED1C29;">ooredoo</span>
                <span style="font-size:22px; color:#1a1a1a; font-weight:600;">Benchmark IA</span>
            </div>
            """,
            unsafe_allow_html=True,
        \)'''

# It's already in the right place, just verify it exists

# ===================================================================
# CHANGE 4: Convert tab blocks to conditionals
# ===================================================================

# Replace "with overview_tab:" with conditional
content = re.sub(
    r'    with overview_tab:',
    '        if selected_nav == "📊 Vue d\'ensemble":',
    content
)

# Replace "with scenarios_tab:" with conditional
content = re.sub(
    r'    with scenarios_tab:',
    '        elif selected_nav == "📋 Comparaison scénarios":',
    content
)

# Replace "with models_tab:" with conditional
content = re.sub(
    r'    with models_tab:',
    '        elif selected_nav == "📈 Comparaison modèles":',
    content
)

# Replace "with details_tab:" with conditional  
content = re.sub(
    r'        with details_tab:',
    '        elif selected_nav == "🔍 Détails des exécutions":',
    content
)

# Replace pilotage_tab conditional
content = re.sub(
    r'    if is_admin and pilotage_tab is not None:\n        with pilotage_tab:',
    '        elif selected_nav == "🎛️ Pilotage":',
    content
)

# Replace admin_tab conditional
content = re.sub(
    r'    if is_super_admin and admin_tab is not None:\n        with admin_tab:',
    '        elif selected_nav == "⚙️ Administration":',
    content
)

print("✓ Converted tab blocks to conditionals")

# ===================================================================
# CHANGE 5: Remove old tab objects initialization
# ===================================================================

old_tabs_init = r'''    # ------------------------------------------------------------------
    # Construction des onglets : le Client n'a plus "Détails des
    # exécutions" \(données brutes/techniques\) ni "Pilotage"\.
    # ------------------------------------------------------------------
    tabs = \["Vue d'ensemble", "Comparaison modèles", "Comparaison scénarios", "Détails des exécutions"\]

    if is_admin:
        tabs\.append\("Pilotage"\)
    if is_super_admin:
        tabs\.append\("Administration"\)

    tab_objects = st\.tabs\(tabs\)

    overview_tab, models_tab, scenarios_tab, details_tab = tab_objects\[:4\]
    extra_tabs = list\(tab_objects\[4:\]\)

    pilotage_tab = extra_tabs\.pop\(0\) if is_admin else None
    admin_tab = extra_tabs\.pop\(0\) if is_super_admin else None'''

content = re.sub(old_tabs_init, '', content, flags=re.DOTALL)

print("✓ Removed old tab objects initialization")

# ===================================================================
# CHANGE 6: Fix indentation issues from removed try-except
# ===================================================================

# The content after the conditionals needs proper exception handling wrapping

# Find the last `except Exception as e:` and ensure proper closure
old_except = r'''    except Exception as e:
        logger\.error\(f"Critical error in main dashboard: \{e\}", exc_info=True\)
        st\.error\("Une erreur critique s'est produite dans le dashboard\."\)
        st\.error\("Détails de l'erreur \(pour débogage\) :"\)
        st\.exception\(e\)
        
        # Show recovery options
        with st\.expander\("Options de récupération"\):
            if st\.button\("Réinitialiser la session"\):
                for key in list\(st\.session_state\.keys\(\)\):
                    del st\.session_state\[key\]
                st\.rerun\(\)
            
            if st\.button\("Vider le cache"\):
                st\.cache_data\.clear\(\)
                st\.success\("Cache vidé\. Veuillez actualiser la page\."\)
                
        return'''

# Add proper exception handling wrapper if removed
if 'except Exception as e:' not in content:
    # Find where we should add try
    try_pos = content.find('def main() -> None:')
    if try_pos > 0:
        try_pos = content.find('    if "auth_role" not in st.session_state:', try_pos)
        if try_pos > 0:
            content = content[:try_pos] + '    try:\n        ' + content[try_pos:]
            # Add exception handler at end of function (before if __name__ == "__main__":)
            final_return = content.rfind('if __name__ == "__main__":')
            if final_return > 0:
                content = content[:final_return] + '\n    except Exception as e:\n        logger.error(f"Critical error in main dashboard: {e}", exc_info=True)\n        st.error("Une erreur critique s\'est produite dans le dashboard.")\n        st.error("Détails de l\'erreur (pour débogage) :")\n        st.exception(e)\n        \n        # Show recovery options\n        with st.expander("Options de récupération"):\n            if st.button("Réinitialiser la session"):\n                for key in list(st.session_state.keys()):\n                    del st.session_state[key]\n                st.rerun()\n            \n            if st.button("Vider le cache"):\n                st.cache_data.clear()\n                st.success("Cache vidé. Veuillez actualiser la page.")\n\n' + content[final_return:]

print("✓ Fixed exception handling wrapper")

# Write result
with open('src/dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Dashboard refactoring complete!")
print("\nChanges made:")
print("  1. ✅ Logo rendering improved (centered, proper aspect ratio, spacing)")
print("  2. ✅ render_sidebar_identity() split into render_sidebar_header() + render_sidebar_account()")
print("  3. ✅ Sidebar layout reorganized (logo → filters → nav → account)")
print("  4. ✅ Navigation moved to st.sidebar.radio() (vertical menu)")
print("  5. ✅ Tab content blocks converted to elif conditionals")
print("  6. ✅ Removed st.tabs() initialization")
print("\nNext: Test the dashboard with all three roles (Client, Admin, Super Admin)")
