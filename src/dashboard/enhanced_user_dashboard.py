"""
Enhanced User Dashboard with KPIs, Model Recommendations, and Performance Metrics
Designed for regular users (non-admins) to view their department's performance
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from src.database.connection import engine
from src.dashboard.formatting import safe_format_score, safe_format_cost, safe_format_latency
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def render_enhanced_user_dashboard(user_email: str, user_role: str, user_department: str = None):
    """
    Render the enhanced user dashboard with:
    - Recommended model card
    - Key KPI metrics
    - Comparative table of model performance
    - Option to view generated responses
    """
    st.title("📊 Votre Tableau de Bord")
    
    # Get user's department if not provided
    if not user_department:
        user_department = _get_user_department(user_email)
    
    if not user_department:
        st.warning("⚠️ Aucun département associé à votre compte. Contactez votre administrateur.")
        return
    
    st.markdown(f"**Département:** {user_department}")
    st.markdown("---")
    
    # Load performance data for user's department
    dept_data = _load_department_performance(user_department)
    
    if dept_data.empty:
        st.info(f"📝 Aucune exécution disponible pour le département **{user_department}**.")
        st.markdown(
            "Les benchmarks seront visibles ici une fois que les administrateurs auront lancé "
            "des évaluations pour votre département."
        )
        return
    
    # Section 1: Recommended Model Card
    st.subheader("🎯 Modèle Recommandé")
    _render_recommended_model_card(dept_data, user_department)
    
    st.markdown("---")
    
    # Section 2: KPI Metrics
    st.subheader("📈 Indicateurs Clés de Performance (KPIs)")
    _render_kpi_metrics(dept_data)
    
    st.markdown("---")
    
    # Section 3: Comparative Model Performance Table
    st.subheader("📊 Performances Comparatives des Modèles")
    _render_comparative_table(dept_data, user_department)
    
    st.markdown("---")
    
    # Section 4: Performance Over Time (if enough data)
    if len(dept_data) >= 10:
        st.subheader("📉 Évolution des Performances")
        _render_performance_trends(dept_data)


def _get_user_department(email: str) -> str:
    """Get the user's department from the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT departement FROM utilisateurs WHERE email = :email"),
                {"email": email}
            ).fetchone()
            
            if result and result.departement:
                return result.departement
            return None
    except Exception as e:
        logger.error(f"Error fetching user department: {e}")
        return None


def _load_department_performance(department: str) -> pd.DataFrame:
    """Load all execution performance data for a specific department"""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT
                    e.id AS execution_id,
                    e.scenario_id,
                    s.nom_cas_usage,
                    s.departement,
                    s.prompt,
                    m.id AS modele_id,
                    m.nom AS modele_nom,
                    m.fournisseur,
                    m.cout_par_1k_tokens,
                    e.reponse_generee,
                    e.latence_secondes,
                    e.cout_estime,
                    e.date_execution
                FROM executions e
                JOIN scenarios s ON s.id = e.scenario_id
                JOIN modeles m ON m.id = e.modele_id
                WHERE s.departement = :department
                  AND e.id IN (
                      SELECT DISTINCT sc.execution_id FROM scores sc
                      WHERE sc.methode = 'ragas'
                        AND COALESCE(sc.is_legacy, FALSE) = FALSE
                        AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                  )
                ORDER BY e.date_execution DESC
            """)
            
            df = pd.read_sql(query, conn, params={"department": department})
            
            if df.empty:
                return df
            
            # Fetch RAGAS scores
            execution_ids = df["execution_id"].tolist()
            scores_query = text("""
                SELECT execution_id, critere, note
                FROM scores
                WHERE execution_id = ANY(:ids)
                  AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                  AND methode = 'ragas'
                  AND COALESCE(is_legacy, FALSE) = FALSE
            """)
            
            scores = pd.read_sql(scores_query, conn, params={"ids": execution_ids})
            
            # Pivot scores
            pivot_scores = scores.pivot_table(
                index="execution_id",
                columns="critere",
                values="note",
                aggfunc="first"
            ).reset_index()
            
            # Merge with main df
            df = df.merge(pivot_scores, on="execution_id", how="left")
            
            # Calculate global score
            score_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            df["score_global"] = df[score_cols].mean(axis=1)
            
            return df
            
    except Exception as e:
        logger.error(f"Error loading department performance: {e}")
        return pd.DataFrame()


def _render_recommended_model_card(df: pd.DataFrame, department: str):
    """Render a card showing the recommended model for the department"""
    # Calculate average scores per model
    model_scores = df.groupby("modele_nom").agg({
        "score_global": "mean",
        "latence_secondes": "mean",
        "cout_estime": "mean",
        "execution_id": "count"
    }).reset_index()
    
    model_scores.columns = ["modele", "avg_score", "avg_latency", "avg_cost", "num_executions"]
    
    # Filter models with at least 3 executions for reliability
    reliable_models = model_scores[model_scores["num_executions"] >= 3]
    
    if reliable_models.empty:
        st.info("📊 Données insuffisantes pour recommander un modèle (minimum 3 exécutions par modèle).")
        return
    
    # Rank by score (primary), then by latency (secondary)
    reliable_models["rank_score"] = reliable_models["avg_score"].rank(ascending=False)
    reliable_models["rank_latency"] = reliable_models["avg_latency"].rank(ascending=True)
    reliable_models["combined_rank"] = reliable_models["rank_score"] * 0.7 + reliable_models["rank_latency"] * 0.3
    
    recommended = reliable_models.sort_values("combined_rank").iloc[0]
    
    # Display recommendation card
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(
            f"""
            <div style='
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 24px;
                border-radius: 12px;
                color: white;
            '>
                <div style='font-size: 16px; opacity: 0.9; margin-bottom: 8px;'>
                    Pour le département <strong>{department}</strong>
                </div>
                <div style='font-size: 32px; font-weight: 700; margin-bottom: 16px;'>
                    {recommended['modele']}
                </div>
                <div style='font-size: 14px; opacity: 0.85;'>
                    Score moyen: <strong>{recommended['avg_score']:.1%}</strong> · 
                    Latence: <strong>{recommended['avg_latency']:.2f}s</strong> · 
                    Basé sur <strong>{int(recommended['num_executions'])}</strong> exécutions
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.metric(
            label="Score de Précision",
            value=f"{recommended['avg_score']:.1%}",
            delta=None
        )
        st.metric(
            label="Temps de Réponse",
            value=f"{recommended['avg_latency']:.2f}s",
            delta=None
        )


def _render_kpi_metrics(df: pd.DataFrame):
    """Render key performance indicator metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Average Accuracy (Global Score)
    avg_accuracy = df["score_global"].mean()
    with col1:
        st.metric(
            label="📊 Précision Moyenne",
            value=f"{avg_accuracy:.1%}" if pd.notna(avg_accuracy) else "N/A",
            help="Score moyen de tous les modèles sur vos scénarios"
        )
    
    # KPI 2: Average Latency
    avg_latency = df["latence_secondes"].mean()
    with col2:
        st.metric(
            label="⚡ Latence Moyenne",
            value=f"{avg_latency:.2f}s" if pd.notna(avg_latency) else "N/A",
            help="Temps de réponse moyen des modèles"
        )
    
    # KPI 3: Total Cost
    total_cost = df["cout_estime"].sum()
    with col3:
        st.metric(
            label="💰 Coût Total",
            value=f"${total_cost:.4f}" if pd.notna(total_cost) else "N/A",
            help="Coût cumulé de toutes les exécutions"
        )
    
    # KPI 4: Number of Executions
    num_executions = len(df)
    with col4:
        st.metric(
            label="🔢 Nombre d'Exécutions",
            value=f"{num_executions}",
            help="Total des benchmarks réalisés"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Secondary KPIs - RAGAS metrics
    st.markdown("**Métriques RAGAS Détaillées:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_faithfulness = df["faithfulness"].mean()
        st.metric(
            label="✅ Faithfulness",
            value=f"{avg_faithfulness:.1%}" if pd.notna(avg_faithfulness) else "N/A",
            help="Fidélité de la réponse au contexte"
        )
    
    with col2:
        avg_relevancy = df["answer_relevancy"].mean()
        st.metric(
            label="🎯 Answer Relevancy",
            value=f"{avg_relevancy:.1%}" if pd.notna(avg_relevancy) else "N/A",
            help="Pertinence de la réponse à la question"
        )
    
    with col3:
        avg_precision = df["context_precision"].mean()
        st.metric(
            label="🔍 Context Precision",
            value=f"{avg_precision:.1%}" if pd.notna(avg_precision) else "N/A",
            help="Précision du contexte récupéré"
        )
    
    with col4:
        avg_recall = df["context_recall"].mean()
        st.metric(
            label="📝 Context Recall",
            value=f"{avg_recall:.1%}" if pd.notna(avg_recall) else "N/A",
            help="Rappel du contexte pertinent"
        )


def _render_comparative_table(df: pd.DataFrame, department: str):
    """Render a comparative table of model performance"""
    # Aggregate by model
    model_comparison = df.groupby("modele_nom").agg({
        "score_global": ["mean", "std", "count"],
        "latence_secondes": "mean",
        "cout_estime": "sum",
        "faithfulness": "mean",
        "answer_relevancy": "mean",
        "context_precision": "mean",
        "context_recall": "mean"
    }).reset_index()
    
    # Flatten column names
    model_comparison.columns = [
        "Modèle",
        "Score Moyen",
        "Écart-type",
        "Nb Exécutions",
        "Latence Moy.",
        "Coût Total",
        "Faithfulness",
        "Answer Relevancy",
        "Context Precision",
        "Context Recall"
    ]
    
    # Sort by score
    model_comparison = model_comparison.sort_values("Score Moyen", ascending=False)
    
    # Format columns
    model_comparison["Score Moyen"] = model_comparison["Score Moyen"].apply(lambda x: f"{x:.1%}")
    model_comparison["Écart-type"] = model_comparison["Écart-type"].apply(lambda x: f"{x:.3f}")
    model_comparison["Latence Moy."] = model_comparison["Latence Moy."].apply(lambda x: f"{x:.2f}s")
    model_comparison["Coût Total"] = model_comparison["Coût Total"].apply(lambda x: f"${x:.4f}")
    model_comparison["Faithfulness"] = model_comparison["Faithfulness"].apply(lambda x: f"{x:.1%}")
    model_comparison["Answer Relevancy"] = model_comparison["Answer Relevancy"].apply(lambda x: f"{x:.1%}")
    model_comparison["Context Precision"] = model_comparison["Context Precision"].apply(lambda x: f"{x:.1%}")
    model_comparison["Context Recall"] = model_comparison["Context Recall"].apply(lambda x: f"{x:.1%}")
    
    # Display table
    st.dataframe(
        model_comparison,
        use_container_width=True,
        hide_index=True
    )
    
    # Add option to view individual execution responses
    with st.expander("🔍 Voir les réponses générées"):
        selected_model = st.selectbox(
            "Choisir un modèle",
            options=df["modele_nom"].unique(),
            key="response_viewer_model"
        )
        
        if selected_model:
            model_execs = df[df["modele_nom"] == selected_model].sort_values("date_execution", ascending=False).head(10)
            
            for idx, row in model_execs.iterrows():
                with st.container():
                    st.markdown(f"**Scénario:** {row['nom_cas_usage']}")
                    st.markdown(f"**Prompt:** {row['prompt'][:200]}...")
                    st.markdown(f"**Réponse générée:**")
                    st.text_area(
                        label="Response",
                        value=row['reponse_generee'] if pd.notna(row['reponse_generee']) else "N/A",
                        height=150,
                        key=f"response_{row['execution_id']}",
                        label_visibility="collapsed"
                    )
                    st.markdown(
                        f"Score: **{row['score_global']:.1%}** | "
                        f"Latence: **{row['latence_secondes']:.2f}s** | "
                        f"Date: **{row['date_execution'].strftime('%Y-%m-%d %H:%M')}**"
                    )
                    st.markdown("---")


def _render_performance_trends(df: pd.DataFrame):
    """Render performance trends over time"""
    # Convert date_execution to datetime if needed
    df["date_execution"] = pd.to_datetime(df["date_execution"])
    
    # Group by date and model
    daily_performance = df.groupby([df["date_execution"].dt.date, "modele_nom"]).agg({
        "score_global": "mean"
    }).reset_index()
    
    daily_performance.columns = ["date", "modele", "score"]
    
    # Create line chart
    fig = px.line(
        daily_performance,
        x="date",
        y="score",
        color="modele",
        title="Évolution du Score Global par Modèle",
        labels={"date": "Date", "score": "Score Global", "modele": "Modèle"},
        markers=True
    )
    
    fig.update_yaxis(tickformat=".0%")
    fig.update_layout(hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)
