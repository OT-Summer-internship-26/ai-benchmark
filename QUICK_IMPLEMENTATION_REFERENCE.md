# Dashboard Redesign - Quick Implementation Reference

## File to Modify
`src/dashboard/app.py`

## Change 1: Replace render_sidebar_identity() → render_sidebar_header() + render_sidebar_account()

**Line ~1151**: Replace the entire `render_sidebar_identity()` function with:

```python
def render_sidebar_header() -> None:
    """Render improved logo header at TOP of sidebar."""
    st.markdown(
        f"""<div style='display: flex; justify-content: center; align-items: center;
                       padding: 16px 0 12px 0; margin-bottom: 8px;'>
            <img src='data:image/png;base64,{LOGO_B64}' 
                 style='max-width: 140px; height: auto; display: block; object-fit: contain;'
                 alt='Ooredoo Logo'>
        </div>""", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 8px 0; opacity: 0.3;'>", unsafe_allow_html=True)


def render_sidebar_account(email: str, role: str) -> None:
    """Render account/identity section at BOTTOM of sidebar."""
    st.sidebar.divider()
    st.sidebar.markdown(
        f"""<div style='text-align:center; color:white; padding:12px 0;'>
            <div style='font-weight:700; font-size:14px; margin-bottom:4px;'>{email}</div>
            <div style='font-size:11px; letter-spacing:1px; opacity:0.85; margin-bottom:12px;'>{role.upper()}</div>
        </div>""", unsafe_allow_html=True)
    
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

## Change 2: Update main() - Sidebar Setup (after auth check)

**Line ~1210+**: After `if "auth_role" not in st.session_state:` block, replace all the old render_sidebar_identity() and filter setup with:

```python
        # ===================================================================
        # SIDEBAR LAYOUT (NEW DESIGN)
        # ===================================================================
        
        # 1. Logo header
        st.sidebar.markdown("")
        render_sidebar_header()
        
        # 2. Filters
        st.sidebar.header("Filtres")
        load_all = st.sidebar.checkbox(
            "Charger toutes les exécutions (ignorer la limite)", value=False,
            help="Utile pour être sûr de voir tous les scénarios/modèles, même au-delà de la limite ci-dessous.")
        if load_all:
            limit = None
            st.sidebar.caption("Limite désactivée — toutes les exécutions de la base sont chargées.")
        else:
            limit = st.sidebar.slider("Nombre d'exécutions à charger", min_value=10, max_value=2000, value=300, step=10)

        # Load data
        with st.spinner("Chargement des données..."):
            df = load_executions(limit=limit)
            df = format_datetime(df)

        if df.empty:
            st.warning("Aucune exécution disponible dans la base de données.")
            st.info("Veuillez vérifier que des benchmarks ont été exécutés ou contactez votre administrateur.")
            return

        logger.info(f"Loaded {len(df)} executions for dashboard display")

        # 3. API token status
        if is_admin:
            if st.session_state.get("api_token"):
                st.sidebar.caption("✅ API token: présent")
            else:
                st.sidebar.error(f"API token absent — erreur : {st.session_state.get('api_token_error')}")

        # 4. Legacy scores warning
        try:
            with engine.connect() as conn:
                legacy_count = conn.execute(
                    text("SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)")
                ).scalar()
        except Exception:
            legacy_count = 0

        if is_admin and legacy_count and legacy_count > 0:
            st.sidebar.warning(
                f"Attention — {legacy_count} scores heuristiques anciens détectés en base.\n"
                "Ces anciennes métriques peuvent fausser les agrégations. Exécutez `python scripts/cleanup_scores.py --dry-run` puis `--apply` pour nettoyer.")

        # 5. Navigation menu options
        nav_options = ["📊 Vue d'ensemble", "📈 Comparaison modèles", "📋 Comparaison scénarios", "🔍 Détails des exécutions"]
        if is_admin:
            nav_options.append("🎛️ Pilotage")
        if is_super_admin:
            nav_options.append("⚙️ Administration")

        st.sidebar.markdown("---")
        st.sidebar.header("Navigation")
        selected_nav = st.sidebar.radio("Section", options=nav_options, label_visibility="collapsed")

        # 6. Account footer at bottom
        render_sidebar_account(email, role)
```

---

## Change 3: Replace Tab Creation with Conditionals

**Line ~1468**: Replace this:

```python
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

With this:

```python
    # ===================================================================
    # RENDER CONTENT BASED ON SELECTED NAVIGATION ITEM
    # ===================================================================
    
    if selected_nav == "📊 Vue d'ensemble":
```

---

## Change 4: Convert Tab Blocks

For EACH tab block, change:

```python
    with [tab_name]:
```

To:

```python
    elif selected_nav == "[emoji] [Name]":
```

**Specific replacements**:

| Line | Old | New |
|------|-----|-----|
| ~1490 | `with overview_tab:` | `if selected_nav == "📊 Vue d'ensemble":` |
| ~1708 | `with scenarios_tab:` | `elif selected_nav == "📋 Comparaison scénarios":` |
| ~1784 | `with models_tab:` | `elif selected_nav == "📈 Comparaison modèles":` |
| ~1943 | `with details_tab:` | `elif selected_nav == "🔍 Détails des exécutions":` |
| ~2028 | `if is_admin and pilotage_tab is not None:\n    with pilotage_tab:` | `elif selected_nav == "🎛️ Pilotage":` |
| ~2272 | `if is_super_admin and admin_tab is not None:\n    with admin_tab:` | `elif selected_nav == "⚙️ Administration":` |

---

## Change 5: Clean Up (Remove Old Tab Variables)

Delete these lines (they're no longer needed):

```python
overview_tab, models_tab, scenarios_tab, details_tab = tab_objects[:4]
extra_tabs = list(tab_objects[4:])
pilotage_tab = extra_tabs.pop(0) if is_admin else None
admin_tab = extra_tabs.pop(0) if is_super_admin else None
```

---

## Verification Checklist

After making changes, verify:

- [ ] `render_sidebar_header()` function exists
- [ ] `render_sidebar_account()` function exists  
- [ ] `render_sidebar_identity()` function removed
- [ ] `selected_nav = st.sidebar.radio(...)` call exists
- [ ] All old `tab_objects` references removed
- [ ] All `with [tab]:` replaced with `if/elif selected_nav ==`
- [ ] Syntax check: `python -m py_compile src/dashboard/app.py` passes
- [ ] Dashboard starts: `streamlit run src/dashboard/app.py`
- [ ] Logo centered and properly sized
- [ ] Navigation menu visible in sidebar
- [ ] Account footer at bottom of sidebar

---

## Git Commands for Safety

```bash
# Before starting
git checkout src/dashboard/app.py  # Reset if needed

# During work
git diff src/dashboard/app.py  # See what changed

# If something breaks
git checkout src/dashboard/app.py  # Revert to last commit
```

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| IndentationError | Ensure all code inside `if selected_nav ==` is indented 8 spaces |
| `selected_nav` undefined | Make sure `selected_nav = st.sidebar.radio(...)` appears before it's used |
| Logo still stretched | Verify `render_sidebar_header()` is called and has `max-width: 140px` style |
| Navigation menu not showing | Check `render_sidebar_header()` is called BEFORE the radio menu |
| "Se déconnecter" at wrong location | Ensure `render_sidebar_account()` is called AFTER radio menu setup |
| Tab content not rendering | Change `with tab:` to `if selected_nav ==` (note: change indentation too) |

---

## Support

If you encounter issues:
1. Check syntax: `python -m py_compile src/dashboard/app.py`
2. Test dashboard: `streamlit run src/dashboard/app.py`
3. Check GitHub diff: `git diff src/dashboard/app.py`
4. Reference full guide: `DASHBOARD_REDESIGN_GUIDE.md`
