"""The deliberately minimal experience for client accounts.

Client accounts receive one recommendation for their assigned department.
There are no tabs, charts, score tables, execution details, or technical
evaluation vocabulary in this view.
"""

import streamlit as st

from src.dashboard.queries import get_client_department, get_client_recommendation
from src.dashboard.justifications import generate_client_justification


def render_client_recommendation_page(client_email: str) -> None:
    """Render the only data-bearing page available to a client account.

    ``get_client_recommendation`` accepts an email, not a department selected
    in the UI. Its SQL derives and enforces the department from the client
    account, so changing browser state cannot broaden the returned data.
    """
    department = get_client_department(client_email)

    with st.sidebar:
        st.header("Votre espace")
        if department:
            st.selectbox("Votre département", [department], key="client_department")
        else:
            st.caption("Aucun département n’est associé à ce compte.")
        if st.button("Se déconnecter", key="client_logout"):
            for key in ("auth_email", "auth_role", "login_mode", "login_role", "login_stage"):
                st.session_state.pop(key, None)
            st.rerun()

    st.title("Votre recommandation IA")

    if not department:
        st.warning(
            "Votre compte n’est associé à aucun département. "
            "Contactez votre administrateur pour finaliser l’accès."
        )
        return

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

    recommendation = result["recommendation"]
    model_name = recommendation["model_name"]

    # Obtenir l'analyse dynamique basée sur les chiffres concrets du département
    justification_data = generate_client_justification(department, model_name)
    appreciation = justification_data.get("appreciation", "🟢 Modèle recommandé")
    points = justification_data.get("points", [])

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Modèle recommandé pour votre équipe")
            st.header(model_name)
        with col2:
            st.markdown(f"### {appreciation}")

        st.markdown(
            f"Pour les besoins spécifiques de **{department}**, ce modèle apporte les réponses "
            "les plus sûres et les plus adaptées parmi l'ensemble des solutions évaluées."
        )
        
        st.markdown("---")
        st.markdown(f"#### {justification_data.get('title', 'Pourquoi ce choix ?')}")
        for pt in points:
            st.markdown(f"- {pt}")

