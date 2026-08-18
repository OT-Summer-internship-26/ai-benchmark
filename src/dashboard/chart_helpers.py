import streamlit as st

def chart_caption(quoi: str, comment_lire: str, conclusion: str) -> None:
    """Affiche une légende pédagogique sous un graphique.
    À appeler juste après chaque st.vega_lite_chart / st.table / st.dataframe.
    """
    st.caption(
        f"📊 **Ce graphique montre** : {quoi}  \n"
        f"👀 **Comment le lire** : {comment_lire}  \n"
        f"✅ **À retenir** : {conclusion}"
    )