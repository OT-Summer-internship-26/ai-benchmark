"""The deliberately minimal experience for client accounts.

Client accounts receive one recommendation for their assigned department.
Department comes ONLY from utilisateurs.departement (enforced server-side).
There are no tabs, charts, score tables, execution details, or technical
evaluation vocabulary in this view.
"""

import streamlit as st
import pandas as pd
from src.dashboard.queries import (
    get_client_department,
    get_client_recommendation,
    load_executions_by_department,
    get_best_model_for_department,
    get_department_summary_stats,
)
from src.dashboard.justifications import generate_client_justification
from src.dashboard.formatting import safe_format_score, safe_format_cost, safe_format_latency
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


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


def render_client_recommendation_page(client_email: str) -> None:
    """Render the enhanced client dashboard with KPIs, recommendations, and comparison table.

    ``get_client_recommendation`` and ``load_executions_by_department`` both accept
    an email, not a department selected in the UI. Their SQL derives and enforces
    the department from the client account, so changing browser state cannot broaden
    the returned data.
    """
    department = get_client_department(client_email)

    with st.sidebar:
        st.header("Votre espace")
        if department:
            st.info(f"**Département:** {department}")
        else:
            st.caption("Aucun département n'est associé à ce compte.")
        
        # Password change button
        if st.button("🔑 Changer mon mot de passe", use_container_width=True):
            st.session_state["show_password_change"] = True
            st.rerun()
        
        if st.button("🚪 Se déconnecter", key="client_logout", use_container_width=True):
            for key in ("auth_email", "auth_role", "auth_role_key", "auth_user_id", "auth_department", "login_mode"):
                st.session_state.pop(key, None)
            st.rerun()

    st.title("📊 Votre Tableau de Bord IA")

    if not department:
        st.warning(
            "Votre compte n'est associé à aucun département. "
            "Contactez votre administrateur pour finaliser l'accès."
        )
        return

    # Section 1: Executive Summary Card (Recommended Model)
    st.subheader("🎯 Modèle Recommandé")
    
    result = get_client_recommendation(client_email)
    status = result["status"]

    if status == "no_data":
        st.info(
            "Aucune donnée disponible pour votre département pour le moment. "
            "La recommandation apparaîtra après les premiers tests."
        )
        return

    if status == "insufficient_data":
        st.info(
            "Les tests disponibles ne permettent pas encore de recommander "
            "un modèle avec suffisamment de confiance pour votre département."
        )
        return

    # Get detailed model info
    best_model = get_best_model_for_department(department, min_executions=2)
    
    if best_model:
        model_name = best_model["model_name"]
        avg_score = best_model["avg_score"]
        avg_latency = best_model["avg_latency"]
        num_scenarios = best_model["num_scenarios"]
        num_executions = best_model["num_executions"]
        
        # Obtenir l'analyse dynamique
        justification_data = generate_client_justification(department, model_name)
        appreciation = justification_data.get("appreciation", "🟢 Modèle recommandé")
        points = justification_data.get("points", [])

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {model_name}")
                st.caption(f"Pour le département **{department}**")
            with col2:
                emoji, label = _score_to_qualitative_label(avg_score)
                st.markdown(f"### {emoji} {label}")

            st.markdown(
                f"Ce modèle apporte les réponses les plus sûres et les plus adaptées "
                f"parmi l'ensemble des solutions évaluées ({num_executions} tests sur {num_scenarios} scénarios)."
            )
            
            st.markdown("---")
            st.markdown(f"#### {justification_data.get('title', 'Pourquoi ce choix ?')}")
            for pt in points:
                st.markdown(f"- {pt}")
    else:
        st.warning("Données insuffisantes pour établir une recommandation.")
        return

    st.markdown("---")

    # Section 2: KPI Metrics
    st.subheader("📈 Indicateurs Clés de Performance")
    
    # Load executions for this department
    dept_data = load_executions_by_department(department, limit=None, ragas_only=True)
    
    if not dept_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        # KPI 1: Average Quality (Qualitative + %)
        avg_quality = dept_data["score_global_display"].mean()
        emoji, quality_label = _score_to_qualitative_label(avg_quality)
        with col1:
            st.metric(
                label="Qualité Moyenne",
                value=f"{emoji} {quality_label}",
                delta=f"{avg_quality:.1%}" if pd.notna(avg_quality) else "N/A",
                help="Qualité moyenne des réponses générées"
            )
        
        # KPI 2: Average Latency
        avg_latency = dept_data["latence_secondes"].mean()
        with col2:
            st.metric(
                label="Temps de Réponse Moyen",
                value=f"{avg_latency:.2f}s" if pd.notna(avg_latency) else "N/A",
                help="Temps moyen de génération des réponses"
            )
        
        # KPI 3: Estimated Cost
        total_cost = dept_data["cout_estime"].sum()
        with col3:
            st.metric(
                label="Coût Équivalent Estimé",
                value=f"${total_cost:.4f}" if pd.notna(total_cost) else "N/A",
                help="Coût cumulé estimé de toutes les exécutions"
            )
        
        # KPI 4: Number of Tests
        num_tests = len(dept_data)
        with col4:
            st.metric(
                label="Nombre de Tests",
                value=f"{num_tests}",
                help="Total des benchmarks réalisés"
            )
    else:
        st.info("Aucune donnée disponible pour afficher les KPIs.")

    st.markdown("---")

    # Section 3: Simplified Model Comparison Table
    st.subheader("📊 Comparaison des Modèles")
    
    if not dept_data.empty:
        # Aggregate by model
        model_comparison = dept_data.groupby("modele_nom").agg({
            "score_global_display": ["mean", "count"],
            "latence_secondes": "mean",
            "cout_estime": "sum",
        }).reset_index()
        
        model_comparison.columns = [
            "Modèle",
            "Score Moyen",
            "Nombre de Tests",
            "Latence Moyenne (s)",
            "Coût Total",
        ]
        
        # Add qualitative labels
        model_comparison["Appréciation"] = model_comparison["Score Moyen"].apply(
            lambda x: _score_to_qualitative_label(x)[1]
        )
        
        # Sort by score
        model_comparison = model_comparison.sort_values("Score Moyen", ascending=False)
        
        # Format for display
        display_df = model_comparison[[
            "Modèle",
            "Appréciation",
            "Score Moyen",
            "Latence Moyenne (s)",
            "Nombre de Tests",
        ]].copy()
        
        display_df["Score Moyen"] = display_df["Score Moyen"].apply(
            lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
        )
        display_df["Latence Moyenne (s)"] = display_df["Latence Moyenne (s)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucune donnée disponible pour la comparaison.")

    st.markdown("---")

    # Section 4: View Generated Responses
    st.subheader("🔍 Exemples de Réponses Générées")
    
    if not dept_data.empty:
        # Group by scenario
        scenarios = dept_data["nom_cas_usage"].unique()
        
        selected_scenario = st.selectbox(
            "Choisir un scénario",
            options=scenarios,
            help="Voir les réponses générées pour ce scénario"
        )
        
        if selected_scenario:
            scenario_data = dept_data[dept_data["nom_cas_usage"] == selected_scenario].sort_values(
                "score_global_display", ascending=False
            ).head(3)  # Top 3 responses for this scenario
            
            for idx, row in scenario_data.iterrows():
                with st.expander(
                    f"{row['modele_nom']} — {_score_to_qualitative_label(row['score_global_display'])[0]} "
                    f"{safe_format_score(row['score_global_display'], as_percentage=True)}"
                ):
                    st.markdown(f"**Réponse générée:**")
                    st.text_area(
                        label="Response",
                        value=row['reponse_generee'] if pd.notna(row['reponse_generee']) else "N/A",
                        height=200,
                        key=f"response_{row['execution_id']}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"⏱️ Latence: {safe_format_latency(row['latence_secondes'])}")
                    with col2:
                        st.caption(f"📅 Date: {row['date_execution'].strftime('%d/%m/%Y %H:%M')}")
    else:
        st.info("Aucune réponse générée disponible.")

    st.markdown("---")
    
    # Footer
    st.caption(
        "💡 **Note:** Les indicateurs affichés concernent uniquement votre département. "
        "Pour plus d'informations, contactez votre administrateur."
    )
