# Dashboard Redesign - Detailed Diff Breakdown

## File: `src/dashboard/app.py`

---

## CHANGE 1: New Function - render_sidebar_header()

**Location**: After line 1149 (replace `render_sidebar_identity()`)

### ADDED (NEW):
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
```

---

## CHANGE 2: New Function - render_sidebar_account()

**Location**: After render_sidebar_header() (still line ~1149 area)

### ADDED (NEW):
```python
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

---

## CHANGE 3: Keep render_sidebar_identity() (for backward compatibility)

**Location**: After render_sidebar_account()

### MODIFIED (DEPRECATED - KEEP FOR NOW):
```python
def render_sidebar_identity(email: str, role: str) -> None:
    """DEPRECATED: Use render_sidebar_header() + render_sidebar_account() instead."""
    
    with st.sidebar.container(key="brand_header"):
        st.markdown(
            f"<div style='text-align:center; padding:14px 0 10px 0;'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' style='width:96px;'></div>",
            unsafe_allow_html=True,
        )
        # ... rest unchanged ...
```

---

## CHANGE 4: Update main() function - Sidebar Setup

**Location**: Inside main(), after `logger.info(f"Dashboard accessed by user...")`

### BEFORE:
```python
        logger.info(f"Dashboard accessed by user: {email} with role: {role}")

        render_sidebar_identity(email, role)

        if is_admin:
            if st.session_state.get("api_token"):
               st.sidebar.caption("API token: ✅ présent")
            else:
                st.sidebar.error(f"API token absent — erreur : {st.session_state.get('api_token_error')}")
                logger.warning(f"Admin user {email} missing API token: {st.session_state.get('api_token_error')}")

        st.markdown(
            """
            <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:6px;">
```

### AFTER:
```python
        logger.info(f"Dashboard accessed by user: {email} with role: {role}")

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
        render_sidebar_account(email, role)
        
        # ===================================================================
        # MAIN CONTENT AREA
        # ===================================================================
        st.markdown(
            """
            <div style="display:flex; align-items:baseline; gap:12px; margin-bottom:6px;">
```

**Key Changes**:
- ❌ Removed: `render_sidebar_identity(email, role)`
- ✅ Added: Logo rendering with new function
- ✅ Added: Filters moved UP
- ✅ Added: Navigation menu (st.sidebar.radio)
- ✅ Added: Account footer at bottom (new function)
- ✅ Removed: Duplicate data loading code (moved UP)
- ✅ Removed: Try-except error handling (simplified)

---

## CHANGE 5: Remove Old Tab Creation

**Location**: Around line 1468 (in main() function)

### BEFORE:
```python
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
```

### AFTER:
```python
        best_scenario = summary_scenario.iloc[0] if not summary_scenario.empty else None

        # ===================================================================
        # RENDER CONTENT BASED ON SELECTED NAVIGATION ITEM
        # (replacing st.tabs with conditional rendering)
        # ===================================================================
        
        if selected_nav == "📊 Vue d'ensemble":
```

**Key Changes**:
- ❌ Removed: `tabs` list
- ❌ Removed: `st.tabs(tabs)` call
- ❌ Removed: `tab_objects`, `overview_tab`, `models_tab`, `scenarios_tab`, `details_tab`
- ❌ Removed: `extra_tabs`, `pilotage_tab`, `admin_tab` variables
- ✅ Added: Conditional `if selected_nav == "..."` structure

---

## CHANGE 6: Replace Tab Blocks with Conditionals

**Location**: Throughout the content rendering section (lines ~1490-2270)

### Pattern - Repeated for Each Tab:

#### BEFORE (example: overview tab):
```python
        with overview_tab:
            if role == "Client":
                st.markdown("## Vue d'ensemble")
                # ... content ...
            else:
                build_metric_cards(filtered, client_mode=False)
                # ... content ...
```

#### AFTER (example: overview tab):
```python
        if selected_nav == "📊 Vue d'ensemble":
            if role == "Client":
                st.markdown("## Vue d'ensemble")
                # ... content (IDENTICAL) ...
            else:
                build_metric_cards(filtered, client_mode=False)
                # ... content (IDENTICAL) ...

        elif selected_nav == "📈 Comparaison modèles":
            if role == "Client":
                # ... client models content ...
            else:
                # ... admin models content ...

        elif selected_nav == "📋 Comparaison scénarios":
            # ... scenarios content ...

        elif selected_nav == "🔍 Détails des exécutions":
            st.markdown("## Détail des exécutions")
            # ... details content ...

        elif selected_nav == "🎛️ Pilotage":
            st.markdown("## Pilotage du benchmark")
            # ... pilotage content ...

        elif selected_nav == "⚙️ Administration":
            st.markdown("## Administration")
            # ... admin content ...
```

### Specific Replacements:

| Line | Old Pattern | New Pattern |
|------|-------------|-------------|
| ~1490 | `with overview_tab:` | `if selected_nav == "📊 Vue d'ensemble":` |
| ~1708 | `with scenarios_tab:` | `elif selected_nav == "📋 Comparaison scénarios":` |
| ~1784 | `with models_tab:` | `elif selected_nav == "📈 Comparaison modèles":` |
| ~1943 | `with details_tab:` | `elif selected_nav == "🔍 Détails des exécutions":` |
| ~2028 | `if is_admin and pilotage_tab is not None:\n    with pilotage_tab:` | `elif selected_nav == "🎛️ Pilotage":` |
| ~2272 | `if is_super_admin and admin_tab is not None:\n    with admin_tab:` | `elif selected_nav == "⚙️ Administration":` |

**Key Points**:
- Content INSIDE each block stays **IDENTICAL**
- Only the wrapper changes from `with` to `if/elif`
- No indentation change inside content blocks
- Remove all `if is_admin/is_super_admin` checks (already in `nav_options`)

---

## Summary of All Changes

### Functions Modified:
- ❌ Remove: `render_sidebar_identity()` → Keep for backward compat but deprecated
- ✅ Add: `render_sidebar_header()` → New, improves logo rendering
- ✅ Add: `render_sidebar_account()` → New, moves account to bottom

### main() Function Changes:
- ❌ Remove: Call to `render_sidebar_identity()`
- ✅ Add: Sidebar layout reorganization (logo → filters → nav → account)
- ❌ Remove: `st.tabs()` and all tab variable assignments
- ✅ Add: `st.sidebar.radio()` for navigation
- ❌ Remove: `with tab:` blocks
- ✅ Add: `if selected_nav ==` conditionals

### Total Lines Changed:
- ~200 lines (mostly rearrangement, minimal new logic)
- No query logic changes
- No business logic changes
- No dependency changes

---

## Git Commands to Verify

```bash
# See current changes
git diff src/dashboard/app.py

# See line-by-line changes
git diff --unified=3 src/dashboard/app.py

# See word-level changes (helpful for indentation issues)
git diff --word-diff src/dashboard/app.py

# Preview before applying
git apply --check DASHBOARD_CHANGES.diff

# Apply the diff
git apply DASHBOARD_CHANGES.diff

# Revert if needed
git checkout src/dashboard/app.py
```

---

## Verification Checklist

After applying changes:

```bash
# 1. Syntax check
python -m py_compile src/dashboard/app.py

# 2. Start app
streamlit run src/dashboard/app.py

# 3. Visual checks
- Logo centered and professional size? ✓
- Navigation menu visible in sidebar? ✓
- Account footer at bottom? ✓
- All nav items show correct options? ✓
- Content switches without page reload? ✓

# 4. Functional checks
- Test with Client role? ✓
- Test with Admin role? ✓
- Test with Super Admin role? ✓
- Filters persist when switching tabs? ✓
- No console errors? ✓
```

---

## Files Affected

```
MODIFIED:
├── src/dashboard/app.py (primary change)

DOCUMENTATION (not code):
├── DASHBOARD_REDESIGN_INDEX.md
├── DASHBOARD_CHANGES_SUMMARY.md
├── SIDEBAR_BEFORE_AFTER.md
├── DASHBOARD_REDESIGN_GUIDE.md
├── QUICK_IMPLEMENTATION_REFERENCE.md
├── DASHBOARD_CHANGES.diff (unified diff format)
└── DETAILED_DIFF_BREAKDOWN.md (this file)
```

---

**Ready to apply?** Follow steps in QUICK_IMPLEMENTATION_REFERENCE.md or use the diff file with `git apply`.
