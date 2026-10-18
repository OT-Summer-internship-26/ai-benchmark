"""Modern executive-style client dashboard.

Client accounts receive a visually engaging recommendation for their assigned
department, structured as a card-grid layout with KPIs, charts, and response
examples — all with Ooredoo branding.

Department comes ONLY from utilisateurs.departement (enforced server-side).
There are no tabs, raw score tables, or technical evaluation vocabulary.
"""

import streamlit as st
import pandas as pd
import html as _html
import plotly.graph_objects as go

from src.dashboard.queries import (
    get_client_department,
    get_client_recommendation,
    get_scenario_catalog,
    load_executions_by_department,
    get_best_model_for_department,
    get_department_summary_stats,
)
from src.dashboard.justifications import generate_client_justification
from src.dashboard.formatting import (
    safe_format_score,
    safe_format_cost,
    safe_format_latency,
)
from src.dashboard.admin_charts import apply_card_layout, OOREDOO_RED, FULL_PALETTE
from src.dashboard.logo import LOGO_B64
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ── Ooredoo colour tokens ──────────────────────────────────────────────
_GREEN = "#00D27A"
_ORANGE = "#F5803E"
_RED = OOREDOO_RED
_BLUE = "#2C7BE5"
_GRAY = "#6B7280"
_LIGHT_GRAY = "#F3F4F6"


def _score_to_qualitative_label(score: float | None) -> tuple[str, str]:
    """Convert score to qualitative label with emoji and color.

    Returns: (emoji, label_text)
    """
    if score is None or pd.isna(score):
        return "⚪", "Non évalué"
    if score >= 0.85:
        return "🟢", "Excellent"
    if score >= 0.70:
        return "🟡", "Bon"
    if score >= 0.50:
        return "🟠", "Correct"
    return "🔴", "À améliorer"


def _score_badge_html(score: float | None, large: bool = False) -> str:
    """Return an inline HTML badge coloured by score tier."""
    if score is None or pd.isna(score):
        bg, fg, text = _GRAY, "#fff", "N/A"
    elif score >= 0.70:
        bg, fg, text = _GREEN, "#fff", f"{score:.1%}"
    elif score >= 0.40:
        bg, fg, text = _ORANGE, "#fff", f"{score:.1%}"
    else:
        bg, fg, text = _RED, "#fff", f"{score:.1%}"

    pad = "6px 16px" if large else "3px 10px"
    fs = "16px" if large else "13px"
    return (
        f'<span style="background:{bg};color:{fg};padding:{pad};'
        f'border-radius:14px;font-size:{fs};font-weight:700;">{text}</span>'
    )


# ── Standard Ooredoo brand header (client-facing) ──────────────────────

def render_client_header(
    department: str = "",
    last_date: pd.Timestamp | str | None = None,
) -> None:
    """Render the standard Ooredoo logo, title, department subtitle, and status pill."""
    col1, col2, col3 = st.columns([1, 3.2, 2.2])

    with col1:
        st.markdown(
            f'<img src="data:image/png;base64,{LOGO_B64}" style="width:120px; margin-top:8px;">',
            unsafe_allow_html=True,
        )

    with col2:
        dept_str = f" : <b>{_html.escape(department)}</b>" if department else ""
        st.markdown(
            f"""
            <div style="padding-top:10px;">
                <span style="font-size:26px; color:#1a1a1a; font-weight:700; letter-spacing:-0.5px;">Benchmark IA</span>
                <p style="color:#6B7280; font-size:14px; margin-top:2px; margin-bottom:0;">
                    Personnalisé pour le département{dept_str}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        if last_date is not None and pd.notna(last_date):
            if hasattr(last_date, "strftime"):
                date_str = last_date.strftime("%d/%m/%Y %H:%M")
            else:
                date_str = str(last_date)
            badge_html = (
                f'<div style="padding-top:16px; text-align:right;">'
                f'<span style="display:inline-block; background:linear-gradient(135deg, #ED1C24 0%, #A80F17 100%); '
                f'color:white; padding:6px 14px; border-radius:20px; font-size:12.5px; font-weight:600; '
                f'box-shadow: 0 2px 6px rgba(237, 28, 36, 0.2);">'
                f'📅 Dernière exécution : {date_str}</span>'
                f'</div>'
            )
        else:
            badge_html = (
                f'<div style="padding-top:16px; text-align:right;">'
                f'<span style="display:inline-block; background:#E5E7EB; '
                f'color:#374151; padding:6px 14px; border-radius:20px; font-size:12.5px; font-weight:600;">'
                f'⚡ Espace Client Actif</span>'
                f'</div>'
            )
        st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin-top:12px; margin-bottom:16px; border:0; border-top:1px solid #E5E7EB;'>",
        unsafe_allow_html=True,
    )


# ── Plotly chart builder (client-facing) ────────────────────────────────

def _build_client_model_comparison(dept_data: pd.DataFrame) -> go.Figure | None:
    """Horizontal bar chart: top-5 models — score (colour) vs latency (bar length)."""
    if dept_data.empty:
        return None

    agg = (
        dept_data.groupby("modele_nom")
        .agg(
            score_moyen=("score_global_display", "mean"),
            latence_moyenne=("latence_secondes", "mean"),
            nb_tests=("execution_id", "count"),
        )
        .reset_index()
        .sort_values("score_moyen", ascending=False)
        .head(5)
    )
    if agg.empty:
        return None

    agg = agg.sort_values("score_moyen", ascending=True)  # best on top

    fig = go.Figure()

    # Bar: latency (length) coloured by score
    fig.add_trace(go.Bar(
        y=agg["modele_nom"],
        x=agg["score_moyen"],
        orientation="h",
        marker=dict(
            color=agg["score_moyen"],
            colorscale=[[0, _ORANGE], [0.5, _BLUE], [1, _GREEN]],
            line=dict(width=0),
        ),
        text=agg["score_moyen"].apply(lambda v: f"{v:.1%}"),
        textposition="outside",
        textfont=dict(size=12, color="#1a1a1a"),
        customdata=agg[["latence_moyenne", "nb_tests"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score moyen : %{x:.1%}<br>"
            "Latence : %{customdata[0]:.2f}s<br>"
            "Tests : %{customdata[1]}"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        xaxis=dict(
            tickformat=".0%", range=[0, 1.15],
            gridcolor="#EAECEF", title=None,
        ),
        yaxis=dict(title=None),
        height=max(180, len(agg) * 52),
        showlegend=False,
    )
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=10, r=40, t=10, b=10))
    return fig


# ════════════════════════════════════════════════════════════════════════
#  MAIN RENDER FUNCTION
# ════════════════════════════════════════════════════════════════════════

def render_client_recommendation_page(client_email: str) -> None:
    """Render the modern, card-based client dashboard.

    The user's own department (from the DB) is the default selection.
    A sidebar selectbox lets them browse other departments without any
    privilege escalation — data isolation is still enforced per-department
    by ``load_executions_by_department`` (server-side SQL).
    """
    own_department = get_client_department(client_email)

    # ── Sidebar ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Votre espace")

        # Build list of all departments from catalog (read-only, no privilege risk)
        try:
            catalog = get_scenario_catalog()
            all_departments = sorted(catalog["departement"].dropna().unique().tolist())
        except Exception:
            all_departments = []

        if all_departments:
            # Default to the user's own department; fall back to index 0
            default_idx = (
                all_departments.index(own_department)
                if own_department in all_departments
                else 0
            )
            selected_department = st.selectbox(
                "Département",
                options=all_departments,
                index=default_idx,
                key="client_dept_select",
                help="Filtrer le tableau de bord par département",
            )
        else:
            # Fallback: no catalog available — use account department
            selected_department = own_department
            if selected_department:
                st.info(f"**Département :** {selected_department}")
            else:
                st.caption("Aucun département n'est associé à ce compte.")

        if st.button(
            "🔑 Changer mon mot de passe",
            use_container_width=True,
            key="client_pwd_btn",
        ):
            st.session_state["show_password_change"] = True
            st.rerun()

        if st.button(
            "🚪 Se déconnecter",
            key="client_logout",
            use_container_width=True,
        ):
            for key in (
                "auth_email", "auth_role", "auth_role_key",
                "auth_user_id", "auth_department", "login_mode",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    # Use the sidebar selection as the active department for all content below
    department = selected_department

    # ── Check department assignment ─────────────────────────────────────
    if not department:
        render_client_header(department="")
        st.warning(
            "Votre compte n'est associé à aucun département. "
            "Contactez votre administrateur pour finaliser l'accès."
        )
        return

    # ── Data loading (all driven by selected department) ────────────────
    result = get_client_recommendation(client_email)
    status = result["status"]

    # For the hero-card we still use the account's own recommendation;
    # KPIs / charts / examples use the sidebar-selected department.
    best_model = get_best_model_for_department(department, min_executions=2)
    dept_data = load_executions_by_department(department, limit=None, ragas_only=True)

    # ── Brand Header (Ooredoo logo, title, department, execution pill) ──
    last_exec_date = None
    if not dept_data.empty and "date_execution" in dept_data.columns:
        valid_dates = dept_data["date_execution"].dropna()
        if not valid_dates.empty:
            last_exec_date = pd.to_datetime(valid_dates.max())

    if last_exec_date is None:
        try:
            from src.dashboard.queries import get_database_connection
            from sqlalchemy import text
            engine = get_database_connection()
            with engine.connect() as conn:
                res = pd.read_sql(
                    text("SELECT MAX(date_execution) as last_date FROM executions"),
                    conn,
                )
                if not res.empty and pd.notna(res.iloc[0]["last_date"]):
                    last_exec_date = pd.to_datetime(res.iloc[0]["last_date"])
        except Exception:
            pass

    render_client_header(department=department, last_date=last_exec_date)

    # Graceful fallback when the selected department has no data yet
    if dept_data.empty and not best_model:
        st.info(
            f"Aucune donnée disponible pour le département **{department}** "
            "pour le moment. La recommandation apparaîtra après les premiers tests."
        )
        return

    if not best_model:
        st.warning(
            f"Données insuffisantes pour établir une recommandation "
            f"pour **{department}**."
        )
        # Still render KPIs and charts if dept_data exists
        if dept_data.empty:
            return

    if best_model:
        model_name = best_model["model_name"]
        avg_score = best_model["avg_score"]
        avg_latency_model = best_model["avg_latency"]
        num_scenarios = best_model["num_scenarios"]
        num_executions = best_model["num_executions"]

        justification_data = generate_client_justification(department, model_name)
        appreciation = justification_data.get("appreciation", "🟢 Modèle recommandé")
        points = justification_data.get("points", [])

        # ================================================================
        # CARD 1 — Modèle Recommandé (prominent hero card)
        # ================================================================
        with st.container(border=True):
            hero_l, hero_r = st.columns([3, 1])
            with hero_l:
                st.markdown(
                    f'<p style="font-size:13px;color:{_GRAY};margin-bottom:2px;">'
                    f"Recommandation pour <b>{department}</b></p>"
                    f'<h2 style="margin-top:0;margin-bottom:4px;">{model_name}</h2>',
                    unsafe_allow_html=True,
                )
            with hero_r:
                emoji, label = _score_to_qualitative_label(avg_score)
                st.markdown(
                    f'<div style="text-align:right;padding-top:12px;">'
                    f'{_score_badge_html(avg_score, large=True)}'
                    f'<br><span style="font-size:13px;color:{_GRAY};">'
                    f'{emoji} {label}</span></div>',
                    unsafe_allow_html=True,
                )

            # ── Mini KPI row inside hero card ───────────────────────────
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    f'<div style="text-align:center;padding:6px 0;">'
                    f'<span style="font-size:22px;font-weight:700;">'
                    f'{safe_format_score(avg_score, as_percentage=True)}</span>'
                    f'<br><span style="font-size:12px;color:{_GRAY};">Précision</span></div>',
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f'<div style="text-align:center;padding:6px 0;">'
                    f'<span style="font-size:22px;font-weight:700;">'
                    f'{avg_latency_model:.1f}s</span>'
                    f'<br><span style="font-size:12px;color:{_GRAY};">Rapidité</span></div>',
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f'<div style="text-align:center;padding:6px 0;">'
                    f'<span style="font-size:22px;font-weight:700;">'
                    f'{num_scenarios}</span>'
                    f'<br><span style="font-size:12px;color:{_GRAY};">Scénarios</span></div>',
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f'<div style="text-align:center;padding:6px 0;">'
                    f'<span style="font-size:22px;font-weight:700;">'
                    f'{num_executions}</span>'
                    f'<br><span style="font-size:12px;color:{_GRAY};">Tests réalisés</span></div>',
                    unsafe_allow_html=True,
                )

            # ── Justification points (compact, no heading) ─────────────
            with st.expander("Pourquoi ce choix ?", expanded=False):
                for pt in points:
                    st.markdown(f"- {pt}")

    # ================================================================
    # SECTION 2 — KPI Indicateurs Clés de Performance
    # ================================================================
    st.markdown(
        '<p style="font-size:16px;font-weight:600;margin-top:12px;">'
        "📈 Indicateurs Clés de Performance</p>",
        unsafe_allow_html=True,
    )

    if not dept_data.empty:
        avg_quality = dept_data["score_global_display"].mean()
        avg_latency = dept_data["latence_secondes"].mean()
        total_cost = dept_data["cout_estime"].sum()
        num_tests = len(dept_data)

        kc1, kc2, kc3, kc4 = st.columns(4)

        # KPI 1 — Qualité Moyenne
        with kc1:
            with st.container(border=True):
                emoji_q, label_q = _score_to_qualitative_label(avg_quality)
                delta_str = f"{avg_quality:.1%}" if pd.notna(avg_quality) else "N/A"
                # Colour the delta based on quality tier
                if pd.notna(avg_quality) and avg_quality >= 0.70:
                    delta_color = "normal"
                elif pd.notna(avg_quality) and avg_quality >= 0.50:
                    delta_color = "off"
                else:
                    delta_color = "inverse"
                st.metric(
                    label="Qualité Moyenne",
                    value=f"{emoji_q} {label_q}",
                    delta=delta_str,
                    delta_color=delta_color,
                    help="Qualité moyenne des réponses générées",
                )

        # KPI 2 — Temps de Réponse
        with kc2:
            with st.container(border=True):
                st.metric(
                    label="⚡ Temps de Réponse",
                    value=safe_format_latency(avg_latency) if pd.notna(avg_latency) else "N/A",
                    help="Temps moyen de génération des réponses",
                )

        # KPI 3 — Coût Estimé
        with kc3:
            with st.container(border=True):
                st.metric(
                    label="💰 Coût Estimé",
                    value=safe_format_cost(total_cost) if pd.notna(total_cost) else "N/A",
                    help="Coût cumulé estimé de toutes les exécutions",
                )

        # KPI 4 — Nombre de Tests
        with kc4:
            with st.container(border=True):
                st.metric(
                    label="🧪 Nombre de Tests",
                    value=f"{num_tests}",
                    help="Total des benchmarks réalisés",
                )
    else:
        st.info("Aucune donnée disponible pour afficher les KPIs.")

    # ================================================================
    # SECTION 3 — Comparaison visuelle des modèles
    # ================================================================
    st.markdown(
        '<p style="font-size:16px;font-weight:600;margin-top:12px;">'
        "📊 Comparaison des Modèles</p>",
        unsafe_allow_html=True,
    )

    if not dept_data.empty:
        # ── Chart + detail table in ONE card (no gap) ───────────────
        with st.container(border=True):
            st.markdown("**Top 5 — Score moyen par modèle**")
            fig = _build_client_model_comparison(dept_data)
            if fig is not None:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="client_model_bar",
                )
            else:
                st.info("Pas assez de données pour le graphique.")

            # Expander sits inside the same card — no visual break
            with st.expander("📋 Voir le tableau détaillé", expanded=False):
                model_comparison = (
                    dept_data.groupby("modele_nom")
                    .agg(
                        score_moyen=("score_global_display", "mean"),
                        nb_tests=("execution_id", "count"),
                        latence_moyenne=("latence_secondes", "mean"),
                        cout_total=("cout_estime", "sum"),
                    )
                    .reset_index()
                    .sort_values("score_moyen", ascending=False)
                )
                model_comparison["Appréciation"] = model_comparison[
                    "score_moyen"
                ].apply(lambda x: _score_to_qualitative_label(x)[1])

                display_df = model_comparison.rename(columns={
                    "modele_nom": "Modèle",
                    "score_moyen": "Score Moyen",
                    "nb_tests": "Tests",
                    "latence_moyenne": "Latence (s)",
                    "cout_total": "Coût Total",
                })[["Modèle", "Appréciation", "Score Moyen", "Latence (s)", "Tests"]].copy()

                display_df["Score Moyen"] = display_df["Score Moyen"].apply(
                    lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                )
                display_df["Latence (s)"] = display_df["Latence (s)"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                )
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    key="client_model_table",
                )
    else:
        st.info("Aucune donnée disponible pour la comparaison.")

    # ================================================================
    # SECTION 4 — Exemples de Réponses Générées
    # ================================================================
    st.markdown(
        '<p style="font-size:16px;font-weight:600;margin-top:12px;">'
        "🔍 Exemples de Réponses Générées</p>",
        unsafe_allow_html=True,
    )

    if not dept_data.empty:
        scenarios = sorted(dept_data["nom_cas_usage"].unique())

        selected_scenario = st.selectbox(
            "Choisir un scénario",
            options=scenarios,
            help="Voir les réponses générées pour ce scénario",
            key="client_scenario_select",
        )

        if selected_scenario:
            # ONE card per DISTINCT model — best-scoring execution kept
            scenario_rows = (
                dept_data[dept_data["nom_cas_usage"] == selected_scenario]
                .sort_values("score_global_display", ascending=False)
                .drop_duplicates(subset=["modele_nom"], keep="first")
                .reset_index(drop=True)
            )

            if scenario_rows.empty:
                st.info("Aucune réponse disponible pour ce scénario.")
            else:
                for _, row in scenario_rows.iterrows():
                    eid = row["execution_id"]
                    score_val = row.get("score_global_display")
                    response_text = row.get("reponse_generee")
                    has_response = pd.notna(response_text) and str(response_text).strip()

                    with st.container(border=True):
                        # Header row: model name + score badge
                        hdr_l, hdr_r = st.columns([3, 1])
                        with hdr_l:
                            st.markdown(f"**{row['modele_nom']}**")
                        with hdr_r:
                            st.markdown(
                                f'<div style="text-align:right;">'
                                f'{_score_badge_html(score_val)}</div>',
                                unsafe_allow_html=True,
                            )

                        # Response body — dark readable text, compact container
                        if has_response:
                            escaped = _html.escape(str(response_text))
                            st.markdown(
                                f'<div style="'
                                f"background-color:#FFFFFF;"
                                f"border:1px solid #E5E7EB;"
                                f"border-radius:8px;"
                                f"padding:12px 14px;"
                                f"max-height:220px;"
                                f"overflow-y:auto;"
                                f"color:#111827;"
                                f"font-size:14.5px;"
                                f"line-height:1.6;"
                                f"font-family:Inter,system-ui,sans-serif;"
                                f"white-space:pre-wrap;"
                                f"word-break:break-word;"
                                f'">{escaped}</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<p style="color:{_GRAY};font-style:italic;'
                                f'font-size:14px;margin:4px 0;">'
                                "Réponse non disponible (N/A)</p>",
                                unsafe_allow_html=True,
                            )

                        # Footer meta — compact single line
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            st.caption(
                                f"⏱️ {safe_format_latency(row.get('latence_secondes'))}"
                            )
                        with fc2:
                            date_val = row.get("date_execution")
                            if pd.notna(date_val):
                                try:
                                    st.caption(
                                        f"📅 {date_val.strftime('%d/%m/%Y %H:%M')}"
                                    )
                                except Exception:
                                    st.caption(f"📅 {date_val}")
                            else:
                                st.caption("📅 —")
    else:
        st.info("Aucune réponse générée disponible.")

    # ── Footer ──────────────────────────────────────────────────────
    st.caption(
        "💡 **Note :** Les indicateurs affichés concernent uniquement votre "
        "département. Pour plus d'informations, contactez votre administrateur."
    )
