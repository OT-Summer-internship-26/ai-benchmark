import streamlit as st
import pandas as pd
import io
from sqlalchemy import text

from src.database.connection import engine

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import verify_password



@st.cache_data
def load_executions(limit: int = 200) -> pd.DataFrame:
    with engine.connect() as conn:
        executions = pd.read_sql(
            text(
                """
                SELECT
                    e.id AS execution_id,
                    e.scenario_id,
                    s.nom_cas_usage,
                    s.departement,
                    m.id AS modele_id,
                    m.nom AS modele_nom,
                    e.reponse_generee,
                    e.latence_secondes,
                    e.cout_estime,
                    e.date_execution
                FROM executions e
                JOIN scenarios s ON s.id = e.scenario_id
                JOIN modeles m ON m.id = e.modele_id
                ORDER BY e.date_execution DESC
                LIMIT :limit
                """
            ),
            conn,
            params={"limit": limit},
        )

        if executions.empty:
            return executions

        # Fetch only RAGAS criteria (0.0-1.0) to avoid mixing legacy heuristics
        scores = pd.read_sql(
            text(
                "SELECT execution_id, critere, note, commentaire "
                "FROM scores WHERE execution_id IN :ids AND (critere IN ('faithfulness','answer_relevancy','context_precision','context_recall') OR (critere='score_global' AND note <= 1.0))"
            ),
            conn,
            params={"ids": tuple(executions["execution_id"].tolist())},
        )

    if scores.empty:
        executions["score_global_auto"] = None
        executions["score_global_display"] = None
        return executions

    pivot_scores = scores.pivot_table(
        index="execution_id",
        columns="critere",
        values="note",
        aggfunc="first",
    ).reset_index()

    pivot_comments = scores.pivot_table(
        index="execution_id",
        columns="critere",
        values="commentaire",
        aggfunc="first",
    ).reset_index()
    pivot_comments = pivot_comments.rename(
        columns={
            "faithfulness": "faithfulness_comment",
            "answer_relevancy": "answer_relevancy_comment",
            "context_precision": "context_precision_comment",
            "context_recall": "context_recall_comment",
            "score_global": "score_global_comment",
        }
    )

    df = executions.merge(pivot_scores, on="execution_id", how="left")
    df = df.merge(pivot_comments, on="execution_id", how="left")
    df["score_global_auto"] = (
        df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]]
        .mean(axis=1)
        .round(3)
    )
    df["score_global_display"] = df["score_global_auto"]
    return df


def format_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "date_execution" in df.columns:
        df["date_execution"] = pd.to_datetime(df["date_execution"])
    return df


def build_metric_cards(df: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Exécutions", len(df))
    col2.metric("Modèles", df["modele_nom"].nunique())
    col3.metric("Scénarios", df["nom_cas_usage"].nunique())
    col4.metric(
        "Score global moyen",
        f"{round(df['score_global_auto'].mean(), 3):.3f}" if "score_global_auto" in df.columns else "N/A",
    )

ROLE_DISPLAY = {
    "client": "Client",
    "admin": "Admin",
    "super_admin": "Super Admin",
}


def login_form():
    st.title("Connexion — Benchmark IA Ooredoo")
    with st.form("login_form"):
        email = st.text_input("Adresse e-mail").strip()
        password = st.text_input("Mot de passe", type="password").strip()
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        db = SessionLocal()
        try:
            user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        finally:
            db.close()

        if user is None or not verify_password(password, user.mot_de_passe_hash):
            st.error("Identifiants invalides.")
            return

        st.session_state["auth_email"] = user.email
        st.session_state["auth_role"] = ROLE_DISPLAY.get(user.role, user.role)
        st.rerun()
def main() -> None:
    if "auth_role" not in st.session_state:
        login_form()
        st.stop()
    st.set_page_config(
        page_title="Benchmark IA Ooredoo",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Benchmark IA Ooredoo")
    st.markdown(
        "Ce dashboard permet de comparer les résultats de benchmark RAG + LLM, "
        "d’analyser la performance des modèles et de consulter les exécutions détaillées."
    )

    # Simple CSS tweaks for visual polish
    st.markdown(
        """
        <style>
        header {display:none;}
        h1 {font-size:30px; color:#0B3D91;}
        h2 {color:#0B3D91;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Accès")

    email = st.session_state["auth_email"]
    role = st.session_state["auth_role"]
    is_admin = role in ["Admin", "Super Admin"]
    is_super_admin = role == "Super Admin"

    st.sidebar.markdown(f"**Utilisateur** : {email}  ")
    st.sidebar.markdown(f"**Rôle** : {role}")

    if st.sidebar.button("Se déconnecter"):
        st.session_state.pop("auth_email", None)
        st.session_state.pop("auth_role", None)
        st.rerun()

    if role == "Client":
        st.sidebar.info("Mode client : interface simplifiée, sans détails sensibles.")
    elif role == "Admin":
        st.sidebar.info("Mode admin : accès complet aux données métier et aux exports.")
    else:
        st.sidebar.info("Mode super admin : accès complet + administration.")

    st.sidebar.header("Filtres")
    limit = st.sidebar.slider(
        "Nombre d'exécutions à charger",
        min_value=10,
        max_value=200,
        value=100,
        step=10,
    )

    df = load_executions(limit=limit)
    df = format_datetime(df)

    # Vérifier la présence de scores heuristiques anciens et prévenir
    try:
        with engine.connect() as conn:
            legacy_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM scores WHERE critere IN ('completude','structure','fidelite_rag','honnetete') OR (critere='score_global' AND note > 1.0)"
                )
            ).scalar()
    except Exception:
        legacy_count = 0

    if legacy_count and legacy_count > 0:
        st.sidebar.warning(
            f"Attention — {legacy_count} scores heuristiques anciens détectés en base.\n"
            "Ces anciennes métriques peuvent fausser les agrégations. Exécutez `python scripts/cleanup_scores.py --dry-run` puis `--apply` pour nettoyer.`"
        )

    if df.empty:
        st.warning("Aucune exécution disponible dans la base de données.")
        return

    modeles = df["modele_nom"].unique().tolist()
    scenarios = df["nom_cas_usage"].unique().tolist()

    selected_modeles = st.sidebar.multiselect("Modèles", modeles, default=modeles)
    selected_scenarios = st.sidebar.multiselect("Scénarios", scenarios, default=scenarios)

    min_date = df["date_execution"].min().date()
    max_date = df["date_execution"].max().date()
    date_range = st.sidebar.date_input(
        "Période d'exécution",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    filtered = df[
        df["modele_nom"].isin(selected_modeles)
        & df["nom_cas_usage"].isin(selected_scenarios)
        & (df["date_execution"].dt.date >= start_date)
        & (df["date_execution"].dt.date <= end_date)
    ]

    st.sidebar.markdown("---")
    st.sidebar.write(
        "Filtrer par modèle, scénario et période pour comparer les résultats les plus pertinents."
    )

    # Style / affichage
    st.sidebar.markdown("**Affichage & style**")
    palette = st.sidebar.selectbox(
        "Palette de couleurs",
        options=["tableau10", "category10", "viridis", "blues", "inferno"],
        index=0,
    )
    normalize_stacked = st.sidebar.checkbox("Normaliser la pile (proportions)", value=False)

    # Advanced export controls
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Export avancé**")
        all_columns = filtered.columns.tolist()
        default_cols = [c for c in ["execution_id", "modele_nom", "nom_cas_usage", "date_execution", "score_global_display"] if c in all_columns]
        selected_columns_for_export = st.sidebar.multiselect("Colonnes à exporter", options=all_columns, default=default_cols)
    else:
        selected_columns_for_export = ["date_execution", "modele_nom", "nom_cas_usage", "score_global_display"]
        st.sidebar.markdown("---")
        st.sidebar.info("Export avancé disponible uniquement pour Admin et Super Admin.")

    if filtered.empty:
        st.warning("Aucun résultat pour les filtres sélectionnés et la période définie.")
        return

    latest_run = filtered["date_execution"].max()
    st.caption(f"Dernière exécution chargée : {latest_run}")

    metric_names = {
        "score_global_display": "Score global",
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer relevancy",
        "context_precision": "Context precision",
        "context_recall": "Context recall",
        "latence_secondes": "Latence (s)",
    }
    selected_metric_key = st.sidebar.selectbox(
        "Métrique à comparer",
        list(metric_names.values()),
        index=0,
    )
    selected_metric = next(
        key for key, label in metric_names.items() if label == selected_metric_key
    )

    summary_model = (
        filtered.groupby("modele_nom")[
            ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall", "latence_secondes"]
        ]
        .mean()
        .round(3)
        .reset_index()
        .sort_values("score_global_display", ascending=False)
    )

    summary_scenario = (
        filtered.groupby("nom_cas_usage")[
            ["score_global_display", "faithfulness", "answer_relevancy", "context_precision", "context_recall", "latence_secondes"]
        ]
        .mean()
        .round(3)
        .reset_index()
        .sort_values("score_global_display", ascending=False)
    )

    score_plot = (
        summary_model.set_index("modele_nom")[selected_metric].dropna().sort_values(ascending=False)
    )
    score_time_df = (
        filtered.dropna(subset=[selected_metric])
        .groupby(["date_execution", "modele_nom"])[selected_metric]
        .mean()
        .reset_index()
    )

    model_metrics_long = summary_model.melt(
        id_vars=["modele_nom"],
        value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        var_name="critere",
        value_name="note",
    )

    scenario_metrics_long = summary_scenario.melt(
        id_vars=["nom_cas_usage"],
        value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
        var_name="critere",
        value_name="note",
    )

    if selected_metric == "score_global_display":
        selected_metric_label = "score_global_display"
    else:
        selected_metric_label = selected_metric

    score_vs_latency = (
        filtered.dropna(subset=["score_global_display", "latence_secondes"])
        [["modele_nom", "score_global_display", "latence_secondes"]]
        .sort_values(["score_global_display", "latence_secondes"], ascending=[False, True])
    )

    best_model = summary_model.iloc[0] if not summary_model.empty else None
    best_scenario = summary_scenario.iloc[0] if not summary_scenario.empty else None

    tabs = ["Vue d'ensemble", "Comparaison modèles", "Comparaison scénarios", "Détails des exécutions"]
    if is_super_admin:
        tabs.append("Administration")

    overview_tab, models_tab, scenarios_tab, details_tab, *admin_tab = st.tabs(tabs)
    admin_tab = admin_tab[0] if admin_tab else None

    with overview_tab:
        if role == "Client":
            st.markdown("## Vue d'ensemble – client")
            build_metric_cards(filtered)
            st.markdown("#### Top 3 modèles")
            top3 = summary_model.head(3).copy()
            if not top3.empty:
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                top3["score_global_display"] = top3["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(
                    top3.rename(
                        columns={
                            "modele_nom": "Modèle",
                            "score_global_display": "Score global",
                            "latence_secondes": "Latence (s)",
                        }
                    )[["Modèle", "Score global", "Latence (s)"]]
                )
            else:
                st.info("Pas de modèles à afficher pour le Top 3.")

            st.markdown("#### Top 3 scénarios")
            top3_scenarios = summary_scenario.head(3).copy()
            if not top3_scenarios.empty:
                top3_scenarios = top3_scenarios.reset_index(drop=True)
                top3_scenarios.index = top3_scenarios.index + 1
                top3_scenarios["score_global_display"] = top3_scenarios["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(
                    top3_scenarios.rename(
                        columns={
                            "nom_cas_usage": "Scénario",
                            "score_global_display": "Score global",
                            "latence_secondes": "Latence (s)",
                        }
                    )[["Scénario", "Score global", "Latence (s)"]]
                )
            else:
                st.info("Pas de scénarios à afficher pour le Top 3.")

            st.write(
                "Interface client : vue simplifiée avec les principaux indicateurs."
            )
        else:
            build_metric_cards(filtered)
            # Small trend of mean score over time
            daily_mean = (
                filtered.dropna(subset=["score_global_display"])
                .groupby(pd.Grouper(key="date_execution", freq="D"))["score_global_display"]
                .mean()
                .reset_index()
            )
            if not daily_mean.empty:
                st.markdown("#### Tendance moyenne des scores")
                st.vega_lite_chart(
                    data=daily_mean,
                    spec={
                        "mark": {"type": "line", "point": True},
                        "encoding": {
                            "x": {"field": "date_execution", "type": "temporal", "title": "Date"},
                            "y": {"field": "score_global_display", "type": "quantitative", "title": "Score moyen"},
                        },
                    },
                    use_container_width=True,
                )
            st.divider()

            if best_model is not None and best_scenario is not None:
                rec_col1, rec_col2, rec_col3 = st.columns([3, 3, 2])
                # compute delta vs second best
                second_score = summary_model.iloc[1]["score_global_display"] if len(summary_model) > 1 else 0
                delta = best_model["score_global_display"] - second_score
                # Show model name with its score in the value, pass delta only once
                rec_col1.metric(
                    "Modèle recommandé",
                    f"{best_model['modele_nom']} ({best_model['score_global_display']:.3f})",
                    delta=f"{delta:+.3f}",
                )
                rec_col2.metric(
                    "Scénario recommandé",
                    best_scenario["nom_cas_usage"],
                    f"{best_scenario['score_global_display']:.3f}",
                )
                rec_col3.metric(
                    "Scores évalués",
                    int(filtered[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].count().sum()),
                )
            st.divider()

            st.markdown("#### Top 3 modèles")
            top3 = summary_model.head(3).copy()
            if not top3.empty:
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                top3["score_global_display"] = top3["score_global_display"].map(lambda v: f"{v:.3f}")
                top3["latence_secondes"] = top3["latence_secondes"].map(lambda v: f"{v:.2f}s")
                st.table(
                    top3.rename(
                        columns={
                            "modele_nom": "Modèle",
                            "score_global_display": "Score global",
                            "faithfulness": "Faithfulness",
                            "answer_relevancy": "Answer relevancy",
                            "context_precision": "Context precision",
                            "context_recall": "Context recall",
                            "latence_secondes": "Latence (s)",
                        }
                    )
                )
            else:
                st.info("Pas de modèles à afficher pour le Top 3.")

            # Best model per scenario summary
            st.markdown("#### Meilleur modèle par scénario")
            best_per_scenario = (
                filtered.dropna(subset=["score_global_display"])
                .groupby(["nom_cas_usage", "modele_nom"])["score_global_display"]
                .mean()
                .reset_index()
                .sort_values(["nom_cas_usage", "score_global_display"], ascending=[True, False])
                .groupby("nom_cas_usage")
                .first()
                .reset_index()
            )
            if not best_per_scenario.empty:
                best_per_scenario["score_global_display"] = best_per_scenario["score_global_display"].map(lambda v: f"{v:.3f}")
                st.table(best_per_scenario.rename(columns={"nom_cas_usage": "Scénario", "modele_nom": "Meilleur modèle", "score_global_display": "Score"}))
            else:
                st.info("Pas assez de données pour déterminer le meilleur modèle par scénario.")
            st.divider()

            # Export filtered data as CSV
            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exporter CSV des exécutions filtrées",
                data=csv,
                file_name="executions_filtered.csv",
                mime="text/csv",
            )
            if is_admin:
                # Advanced Excel export: multiple sheets (executions, summary_model, summary_scenario)
                try:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                        # write filtered executions (selected columns)
                        if selected_columns_for_export:
                            filtered[selected_columns_for_export].to_excel(writer, index=False, sheet_name="executions")
                        else:
                            filtered.to_excel(writer, index=False, sheet_name="executions")
                        # write summaries
                        summary_model.to_excel(writer, index=False, sheet_name="summary_model")
                        summary_scenario.to_excel(writer, index=False, sheet_name="summary_scenario")
                    excel_bytes = excel_buffer.getvalue()
                    st.download_button(
                        "Exporter Excel multi-feuilles (xlsx)",
                        data=excel_bytes,
                        file_name="executions_filtered_multi.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception:
                    st.info("Export Excel non disponible (vérifiez que 'openpyxl' est installé).")
            else:
                st.info("Export Excel multi-feuilles réservé à Admin et Super Admin.")

            # Stacked bar: répartition des métriques RAGAS par modèle
            st.markdown("#### Répartition des métriques RAGAS par modèle (stacked)")
            stacked_df = model_metrics_long.rename(columns={"modele_nom": "Modèle", "critere": "Critère", "note": "Note"})
            if not stacked_df.empty:
                stacked_spec = {
                    "mark": "bar",
                    "encoding": {
                        "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                        "x": {"aggregate": "sum", "field": "Note", "type": "quantitative"},
                        "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative"},
                        ],
                    },
                }
                if normalize_stacked:
                    # request normalized stacking (proportions)
                    stacked_spec["encoding"]["x"]["stack"] = "normalize"
                st.vega_lite_chart(data=stacked_df, spec=stacked_spec, use_container_width=True)
            else:
                st.info("Aucune donnée RAGAS disponible pour le stacked chart.")

            # Heatmap: modèles vs scénarios (score_global)
            st.markdown("#### Heatmap : score global (scénarios × modèles)")
            heat_order = st.selectbox("Trier heatmap par", options=["Aucun", "Moyenne modèle", "Moyenne scénario"], index=1)
            heat_df = (
                filtered.pivot_table(
                    index="nom_cas_usage", columns="modele_nom", values="score_global_display", aggfunc="mean"
                )
                .reset_index()
                .melt(id_vars=["nom_cas_usage"], var_name="modele_nom", value_name="score")
            )
            heat_df = heat_df.rename(columns={"nom_cas_usage": "Scénario", "modele_nom": "Modèle", "score": "Score"})
            if not heat_df["Score"].isna().all():
                # Apply ordering if requested
                if heat_order == "Moyenne modèle":
                    order = summary_model["modele_nom"].tolist()
                    heat_df["Modèle"] = pd.Categorical(heat_df["Modèle"], categories=order, ordered=True)
                elif heat_order == "Moyenne scénario":
                    scen_order = summary_scenario["nom_cas_usage"].tolist()
                    heat_df["Scénario"] = pd.Categorical(heat_df["Scénario"], categories=scen_order, ordered=True)
                heat_spec = {
                    "mark": "rect",
                    "encoding": {
                        "x": {"field": "Modèle", "type": "nominal"},
                        "y": {"field": "Scénario", "type": "nominal"},
                        "color": {"field": "Score", "type": "quantitative", "scale": {"scheme": palette}},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Score", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=heat_df, spec=heat_spec, use_container_width=True)
            else:
                st.info("Aucune donnée de score global pour produire la heatmap.")

            # Histogrammes : distribution des scores et de la latence
            st.markdown("#### Distributions : score global et latence")
            hist_col1, hist_col2 = st.columns(2)
            score_hist_df = filtered["score_global_display"].dropna().to_frame(name="Score")
            latency_hist_df = filtered["latence_secondes"].dropna().to_frame(name="Latence")
            if not score_hist_df.empty:
                hist_col1.vega_lite_chart(
                    data=score_hist_df,
                    spec={
                        "mark": "bar",
                        "encoding": {"x": {"field": "Score", "type": "quantitative", "bin": True}, "y": {"aggregate": "count", "type": "quantitative"}},
                    },
                    use_container_width=True,
                )
            else:
                hist_col1.info("Pas de scores pour l'histogramme.")

            if not latency_hist_df.empty:
                hist_col2.vega_lite_chart(
                    data=latency_hist_df,
                    spec={
                        "mark": "bar",
                        "encoding": {"x": {"field": "Latence", "type": "quantitative", "bin": True}, "y": {"aggregate": "count", "type": "quantitative"}},
                    },
                    use_container_width=True,
                )
            else:
                hist_col2.info("Pas de latences pour l'histogramme.")
            st.divider()

    with scenarios_tab:
        if role == "Client":
            st.markdown("## Comparaison scénarios – client")
            st.write("Vue simplifiée des scénarios les plus performants.")
            st.table(
                summary_scenario[["nom_cas_usage", "score_global_display"]].head(5).rename(
                    columns={
                        "nom_cas_usage": "Scénario",
                        "score_global_display": "Score global",
                    }
                )
            )
            st.info("Contenu limité : pas de vue détaillée des métriques pour le client.")
        else:
            st.markdown("## Comparaison des scénarios")
            st.write(
                "Comparez les scénarios par score global, métriques dimensions et pertinence."
            )
            st.dataframe(summary_scenario, use_container_width=True)
            st.divider()
            st.markdown("### Top scénarios par score global")
            st.vega_lite_chart(
                data=summary_scenario.rename(columns={"nom_cas_usage": "Scénario", "score_global_display": "Score global"}).head(5),
                spec={
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Score global", "type": "quantitative"},
                        "y": {"field": "Scénario", "type": "nominal", "sort": "-x"},
                        "tooltip": [
                            {"field": "Scénario", "type": "nominal"},
                            {"field": "Score global", "type": "quantitative"},
                        ],
                    },
                },
                use_container_width=True,
            )
            st.divider()
            st.markdown("### Comparaison des critères RAGAS par scénario")
            metrics_by_scenario = summary_scenario.melt(
                id_vars=["nom_cas_usage"],
                value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
                var_name="Critère",
                value_name="Note",
            ).rename(columns={"nom_cas_usage": "Scénario"})
            st.vega_lite_chart(
                data=metrics_by_scenario,
            spec={
                "mark": "bar",
                "encoding": {
                    "x": {"field": "Note", "type": "quantitative"},
                    "y": {"field": "Scénario", "type": "nominal", "sort": "-x"},
                    "color": {"field": "Critère", "type": "nominal"},
                    "tooltip": [
                        {"field": "Scénario", "type": "nominal"},
                        {"field": "Critère", "type": "nominal"},
                        {"field": "Note", "type": "quantitative"},
                    ],
                },
            },
            use_container_width=True,
        )
        st.divider()
        st.markdown("### Top 3 scénarios")
        st.table(summary_scenario.head(3).rename(
            columns={
                "nom_cas_usage": "Scénario",
                "score_global_display": "Score global",
                "faithfulness": "Faithfulness",
                "answer_relevancy": "Answer relevancy",
                "context_precision": "Context precision",
                "context_recall": "Context recall",
                "latence_secondes": "Latence (s)",
            }
        ))

    with models_tab:
        if role == "Client":
            st.markdown("## Comparaison modèles – client")
            st.write("Vue simplifiée des modèles et des scores disponibles.")
            simple_model_table = summary_model[["modele_nom", "score_global_display", "latence_secondes"]].copy()
            simple_model_table["score_global_display"] = simple_model_table["score_global_display"].map(lambda v: f"{v:.3f}")
            simple_model_table["latence_secondes"] = simple_model_table["latence_secondes"].map(lambda v: f"{v:.2f}s")
            st.table(
                simple_model_table.rename(
                    columns={
                        "modele_nom": "Modèle",
                        "score_global_display": "Score global",
                        "latence_secondes": "Latence (s)",
                    }
                )
            )
            st.info("Contenu limité : pas de graphiques avancés pour le client.")
        else:
            st.markdown("## Comparaison modèles")
            st.write(
                "Comparez les modèles par score global, métriques RAGAS, et latence."
            )
            st.dataframe(summary_model, use_container_width=True)
            st.divider()
            # Chart controls for RAGAS comparison
            st.markdown("### Comparaison des critères RAGAS par modèle")
            chart_mode = st.selectbox("Type de graphique RAGAS", options=["Barres groupées", "Barres empilées", "Barres empilées normalisées", "Barres horizontales"], index=0)
            group_by_metric = st.checkbox("Afficher par métrique (small multiples)", value=False)
            metrics_by_model = summary_model.melt(
                id_vars=["modele_nom"],
                value_vars=["faithfulness", "answer_relevancy", "context_precision", "context_recall"],
                var_name="Critère",
                value_name="Note",
            ).rename(columns={"modele_nom": "Modèle"})
            # Build spec dynamically based on controls
            if group_by_metric:
                # small multiples: one chart per metric
                small_spec = {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "Note", "type": "quantitative"},
                        "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                        "color": {"field": "Modèle", "type": "nominal", "legend": None},
                        "column": {"field": "Critère", "type": "nominal"},
                        "tooltip": [
                            {"field": "Modèle", "type": "nominal"},
                            {"field": "Critère", "type": "nominal"},
                            {"field": "Note", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=metrics_by_model, spec=small_spec, use_container_width=True)
            else:
                if chart_mode == "Barres groupées":
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "x": {"field": "Note", "type": "quantitative"},
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                elif chart_mode == "Barres empilées" or chart_mode == "Barres empilées normalisées":
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "x": {"aggregate": "sum", "field": "Note", "type": "quantitative"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                    if chart_mode == "Barres empilées normalisées":
                        spec["encoding"]["x"]["stack"] = "normalize"
                else:
                    # horizontal bars
                    spec = {
                        "mark": "bar",
                        "encoding": {
                            "y": {"field": "Modèle", "type": "nominal", "sort": "-x"},
                            "x": {"field": "Note", "type": "quantitative"},
                            "color": {"field": "Critère", "type": "nominal", "scale": {"scheme": palette}},
                            "tooltip": [
                                {"field": "Modèle", "type": "nominal"},
                                {"field": "Critère", "type": "nominal"},
                                {"field": "Note", "type": "quantitative"},
                            ],
                        },
                    }
                st.vega_lite_chart(data=metrics_by_model, spec=spec, use_container_width=True)
            st.divider()
            # Boxplot: distribution des scores par modèle
            st.markdown("### Distribution des scores par modèle")
            box_df = filtered[["modele_nom", "score_global_display"]].dropna()
            if not box_df.empty:
                box_spec = {
                    "mark": "boxplot",
                    "encoding": {
                        "x": {"field": "modele_nom", "type": "nominal", "title": "Modèle"},
                        "y": {"field": "score_global_display", "type": "quantitative", "title": "Score global"},
                        "color": {"field": "modele_nom", "type": "nominal", "legend": None},
                    },
                }
                st.vega_lite_chart(data=box_df, spec=box_spec, use_container_width=True)
            else:
                st.info("Pas assez de données pour afficher les distributions par modèle.")

            st.divider()
            # Time series: tendance des scores pour les meilleurs modèles
            st.markdown("### Tendance temporelle des meilleurs modèles")
            top_models = summary_model.head(5)["modele_nom"].tolist()
            ts_df = (
                filtered.dropna(subset=["score_global_display"])
                .groupby([pd.Grouper(key="date_execution", freq="D"), "modele_nom"])["score_global_display"]
                .mean()
                .reset_index()
            )
            if not ts_df.empty:
                ts_spec = {
                    "mark": {"type": "line", "point": True},
                    "encoding": {
                        "x": {"field": "date_execution", "type": "temporal", "title": "Date"},
                        "y": {"field": "score_global_display", "type": "quantitative", "title": "Score global"},
                        "color": {"field": "modele_nom", "type": "nominal", "title": "Modèle"},
                        "tooltip": [
                            {"field": "date_execution", "type": "temporal"},
                            {"field": "modele_nom", "type": "nominal"},
                            {"field": "score_global_display", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(data=ts_df[ts_df["modele_nom"].isin(top_models[:3])], spec=ts_spec, use_container_width=True)
            else:
                st.info("Pas de séries temporelles disponibles pour les scores.")

            st.divider()
            # Top-5 models nicely formatted
            st.markdown("### Top 5 modèles — résumé")
            top5 = summary_model.head(5).copy()
            if not top5.empty:
                top5["score_global_display"] = top5["score_global_display"].map(lambda v: f"{v:.3f}")
                top5["latence_secondes"] = top5["latence_secondes"].map(lambda v: f"{v:.2f}s")
                st.table(top5.rename(columns={
                    "modele_nom": "Modèle",
                    "score_global_display": "Score global",
                    "faithfulness": "Faithfulness",
                    "answer_relevancy": "Answer relevancy",
                    "context_precision": "Context precision",
                    "context_recall": "Context recall",
                    "latence_secondes": "Latence",
                }))
            else:
                st.info("Aucun modèle disponible pour le Top 5.")

    with details_tab:
        st.markdown("## Détail des exécutions")
        if role == "Client":
            st.write(
                "Mode client : vous avez accès à un aperçu des exécutions et des scores globaux."
            )
            client_columns = [
                "date_execution",
                "modele_nom",
                "nom_cas_usage",
                "latence_secondes",
                "score_global_auto",
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
            ]
            st.dataframe(
                filtered[client_columns]
                .sort_values("date_execution", ascending=False)
                .rename(
                    columns={
                        "date_execution": "Date",
                        "modele_nom": "Modèle",
                        "nom_cas_usage": "Scénario",
                        "latence_secondes": "Latence (s)",
                        "score_global_auto": "Score global",
                        "faithfulness": "Faithfulness",
                        "answer_relevancy": "Answer relevancy",
                        "context_precision": "Context precision",
                        "context_recall": "Context recall",
                    }
                ),
                use_container_width=True,
            )
            st.info(
                "Données sensibles masquées : pas de réponse générée, pas de coût estimé et pas de détails avancés."
            )
        else:
            st.write(
                "Vous pouvez consulter la liste complète des exécutions récentes, puis sélectionner une entrée pour voir la réponse et les scores détaillés."
            )

            display_columns = [
                "date_execution",
                "modele_nom",
                "nom_cas_usage",
                "departement",
                "latence_secondes",
                "cout_estime",
                "score_global_auto",
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
            ]
            st.dataframe(
                filtered[display_columns]
                .sort_values("date_execution", ascending=False)
                .rename(
                    columns={
                        "date_execution": "Date",
                        "modele_nom": "Modèle",
                        "nom_cas_usage": "Scénario",
                        "departement": "Département",
                        "latence_secondes": "Latence (s)",
                        "cout_estime": "Coût estimé",
                        "score_global_auto": "Score global",
                        "faithfulness": "Faithfulness",
                        "answer_relevancy": "Answer relevancy",
                        "context_precision": "Context precision",
                        "context_recall": "Context recall",
                    }
                ),
                use_container_width=True,
            )

            selected_execution = st.selectbox(
                "Sélectionner une exécution",
                filtered["execution_id"].astype(str).tolist(),
            )
            execution_data = filtered[filtered["execution_id"] == int(selected_execution)].iloc[0]

            st.divider()
            st.markdown("### Exécution sélectionnée")
            left_col, right_col = st.columns(2)
            left_col.markdown(
                f"**Modèle** : {execution_data['modele_nom']}  \n"
                f"**Scénario** : {execution_data['nom_cas_usage']}  \n"
                f"**Département** : {execution_data['departement']}"
            )
            right_col.markdown(
                f"**Score global** : {execution_data['score_global_auto']}  \n"
                f"**Latence** : {execution_data['latence_secondes']:.2f}s  \n"
                f"**Coût estimé** : {execution_data['cout_estime']}"
            )

            with st.expander("Réponse générée"):
                st.code(execution_data["reponse_generee"], language="text")

            st.markdown("### Notes d'évaluation")
            score_items = {
                "Faithfulness": execution_data.get("faithfulness"),
                "Answer relevancy": execution_data.get("answer_relevancy"),
                "Context precision": execution_data.get("context_precision"),
                "Context recall": execution_data.get("context_recall"),
            }
            for label, value in score_items.items():
                st.write(f"- **{label}** : {value}")

    if is_super_admin and admin_tab is not None:
        with admin_tab:
            st.markdown("## Administration")
            st.write("Outils et indicateurs réservés au super admin.")
            admin_metrics_col1, admin_metrics_col2 = st.columns(2)
            admin_metrics_col1.metric("Exécutions chargées", len(df))
            admin_metrics_col1.metric("Modèles", df["modele_nom"].nunique())
            admin_metrics_col2.metric("Scénarios", df["nom_cas_usage"].nunique())
            admin_metrics_col2.metric(
                "Métriques RAGAS présentes",
                int(df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].count().sum()),
            )
            st.markdown("### Export complet des données")
            csv_all = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Télécharger toutes les exécutions (CSV)",
                data=csv_all,
                file_name="executions_all.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()
