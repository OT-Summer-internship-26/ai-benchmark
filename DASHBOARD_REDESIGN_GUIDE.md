# Dashboard UI/UX Redesign Guide

## Overview
This guide documents the required changes to move the Ooredoo IA Benchmark dashboard from horizontal tabs to a vertical sidebar navigation menu, and improve logo rendering.

##Current Architecture (Before)
```
SIDEBAR (Top to Bottom):
├── Logo (stretched, 96px width)
├── Email / Role Badge
├── "Se déconnecter" button
├── Role caption divider
├── Filters section
   ├── Load all checkbox
   ├── Execution limit slider
   ├── API token status (admin)
   ├── Legacy scores warning (admin)
   └── Advanced controls (admin only)

MAIN CONTENT:
├── Title: "ooredoo Benchmark IA"
├── Description text
└── HORIZONTAL TABS (st.tabs()):
    ├── Vue d'ensemble
    ├── Comparaison modèles
    ├── Comparaison scénarios
    ├── Détails des exécutions
    ├── Pilotage (admin only)
    └── Administration (super_admin only)
```

## New Architecture (After)
```
SIDEBAR (Top to Bottom):
├── Logo (centered, max-width 140px, proper aspect ratio) ← NEW STYLE
├── Filters section
   ├── Load all checkbox
   ├── Execution limit slider
   ├── API token status (admin)
   ├── Legacy scores warning (admin)
   └── Advanced controls (admin only)
├── VERTICAL NAVIGATION MENU (st.sidebar.radio()) ← REPLACES TABS
   ├── 📊 Vue d'ensemble
   ├── 📈 Comparaison modèles
   ├── 📋 Comparaison scénarios
   ├── 🔍 Détails des exécutions
   ├── 🎛️ Pilotage (admin only)
   └── ⚙️ Administration (super_admin only)
└── Account footer (at BOTTOM) ← MOVED DOWN
    ├── Email / Role Badge
    └── "🚪 Se déconnecter" button

MAIN CONTENT:
├── Title: "ooredoo Benchmark IA"
├── Description text
└── CONTENT RENDERED DIRECTLY (no st.tabs, conditional elif on selected_nav)
```

## Implementation Steps

### Step 1: Create New Sidebar Helper Functions

Replace `render_sidebar_identity()` with two new functions in `src/dashboard/app.py`:

```python
def render_sidebar_header() -> None:
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
```

### Step 2: Update main() Function - Sidebar Layout

In `main()`, replace the current sidebar setup with:

```python
# (After auth_role check)

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

# Load data (keep existing code)
# [... data loading code ...]

# 3. API token status (admin only)
if is_admin:
    if st.session_state.get("api_token"):
        st.sidebar.caption("✅ API token: présent")
    else:
        st.sidebar.error(f"API token absent — erreur : {st.session_state.get('api_token_error')}")

# 4. Legacy scores warning
try:
    with engine.connect() as conn:
        legacy_count = conn.execute(
            text("SELECT COUNT(*) FROM scores WHERE ...")
        ).scalar()
except Exception:
    legacy_count = 0

if is_admin and legacy_count and legacy_count > 0:
    st.sidebar.warning(f"Attention — {legacy_count} scores heuristiques anciens...")

# 5. Build navigation options
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
render_sidebar_account(email, role)

# ===================================================================
# MAIN CONTENT AREA
# ===================================================================
st.markdown("""
    <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:6px;">
        <span style="font-family:'Trebuchet MS',sans-serif; font-weight:800; font-size:26px; color:#ED1C29;">ooredoo</span>
        <span style="font-size:22px; color:#1a1a1a; font-weight:600;">Benchmark IA</span>
    </div>
""", unsafe_allow_html=True)
st.markdown("Ce dashboard permet de comparer les résultats...")

# [... rest of setup code ...]
```

### Step 3: Convert Tab Blocks to Conditionals

Find the current tab creation code (around line 1468):

**BEFORE:**
```python
tabs = ["Vue d'ensemble", "Comparaison modèles", ...]
tab_objects = st.tabs(tabs)

overview_tab, models_tab, scenarios_tab, details_tab = tab_objects[:4]
extra_tabs = list(tab_objects[4:])
pilotage_tab = extra_tabs.pop(0) if is_admin else None
admin_tab = extra_tabs.pop(0) if is_super_admin else None

with overview_tab:
    if role == "Client":
        # Client overview content
    else:
        # Admin overview content

with models_tab:
    # ...

with scenarios_tab:
    # ...

with details_tab:
    # ...

if is_admin and pilotage_tab is not None:
    with pilotage_tab:
        # Pilotage content

if is_super_admin and admin_tab is not None:
    with admin_tab:
        # Admin content
```

**AFTER:**
```python
if selected_nav == "📊 Vue d'ensemble":
    if role == "Client":
        # Client overview content (SAME CODE, NO INDENTATION CHANGE)
    else:
        # Admin overview content (SAME CODE, NO INDENTATION CHANGE)

elif selected_nav == "📈 Comparaison modèles":
    if role == "Client":
        # Client models content

elif selected_nav == "📋 Comparaison scénarios":
    # Scenarios content

elif selected_nav == "🔍 Détails des exécutions":
    # Executions details content

elif selected_nav == "🎛️ Pilotage":
    # Pilotage content (no outer "if is_admin" check needed - already in nav_options)

elif selected_nav == "⚙️ Administration":
    # Admin content (no outer "if is_super_admin" check needed)
```

**Key point:** The content inside each section stays IDENTICAL. Only the wrapping changes from `with tab_name:` to `elif selected_nav == "tab_name":`.

### Step 4: Clean Up References

- Remove all references to `overview_tab`, `models_tab`, `scenarios_tab`, `details_tab`, `pilotage_tab`, `admin_tab`
- Remove the `tabs = [...]` list
- Remove the `tab_objects = st.tabs(tabs)` call
- Remove the extra tabs extraction code

## Testing Checklist

After implementation, test with all three roles:

### Test 1: Client User
1. Login as client@ooredoo.com
2. ✓ Logo displays centered, not stretched
3. ✓ Filters section visible (Load all checkbox, limit slider)
4. ✓ Navigation menu shows: Vue d'ensemble, Comparaison modèles, Comparaison scénarios, Détails des exécutions
5. ✓ Navigation menu does NOT show: Pilotage, Administration
6. ✓ Account block at bottom shows email and "Se déconnecter"
7. ✓ Clicking each nav item switches content without page reload
8. ✓ Filter selections persist when switching tabs

### Test 2: Admin User
1. Login as admin@ooredoo.com
2. ✓ All Client checks pass
3. ✓ API token status displays  
4. ✓ Navigation menu shows: Pilotage (in addition to client items)
5. ✓ Advanced filters visible (Modèles, Scénarios, Date range)
6. ✓ Affichage & style options visible
7. ✓ Export avancé options visible

### Test 3: Super Admin User
1. Login as superadmin@ooredoo.com (or created super_admin account)
2. ✓ All Admin checks pass
3. ✓ Navigation menu shows: Administration (in addition to all other items)
4. ✓ Administration section loads and displays all admin tools

## Benefits of Redesign

1. **Logo**: Now displays professionally (centered, correct aspect ratio, max 140px)
2. **Navigation**: Vertical menu takes less space, no horizontal scrolling needed
3. **Sidebar Layout**: Logical flow - filters → navigation → account
4. **Account Placement**: Now at bottom of sidebar as "footer", less obtrusive
5. **Session State**: Filter selections preserved when switching sections (already Streamlit behavior)
6. **Role-Based**: Navigation items still conditionally visible based on user role

## Risks & Mitigation

**Risk**: Session state loss when switching tabs
- **Mitigation**: Streamlit radio buttons preserve session state automatically

**Risk**: Indentation errors during conversion
- **Mitigation**: Keep content inside each section identical - only change wrapper from `with` to `elif`

**Risk**: Role-based visibility broken
- **Mitigation**: nav_options list already built conditionally before radio call

## References

- Current file: `src/dashboard/app.py`
- Logo base64: `LOGO_B64` (imported from `src.dashboard.logo`)
- Streamlit docs: https://docs.streamlit.io/ (radio, sidebar, markdown, button)
- French accent preservation: Ensure UTF-8 encoding throughout
