"""The deliberately minimal experience for client accounts.

Client accounts receive one recommendation for their assigned department.
There are no tabs, charts, score tables, execution details, or technical
evaluation vocabulary in this view.
"""

import streamlit as st

from src.dashboard.queries import get_client_department, get_client_recommendation


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
            # This selector has one permitted option only: a client cannot
            # select another team's data.
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
            "un modèle avec suffisamment de confiance."
        )
        return

    recommendation = result["recommendation"]
    model_name = recommendation["model_name"]
    speed_reason = (
        "Ses réponses sont aussi plus rapides que la moyenne des modèles évalués."
        if recommendation["is_faster_than_peers"]
        else "Son délai de réponse convient aux besoins évalués de votre équipe."
    )

    with st.container(border=True):
        st.subheader("Modèle recommandé")
        st.header(model_name)
        st.write(
            f"Pour les besoins de {department}, ce modèle est le choix recommandé : "
            "il donne les réponses les plus fiables parmi les solutions testées."
        )
        st.markdown("**Pourquoi ce choix ?**")
        st.markdown(
            "\n".join(
                [
                    "- Il a donné les meilleurs résultats sur les cas d’usage évalués de votre département.",
                    f"- {speed_reason}",
                    "- Cette recommandation est fondée uniquement sur les besoins de votre équipe.",
                ]
            )
        )
