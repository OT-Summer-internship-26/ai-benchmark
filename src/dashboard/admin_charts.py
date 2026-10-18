"""
Module de génération de graphiques Plotly pour le dashboard Admin.
Tous les chart builders pour les vues Admin/Super Admin.
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Literal
import numpy as np

# Palette Ooredoo + secondaire
OOREDOO_RED = "#ED1C24"
OOREDOO_DARK = "#A80F17"
SECONDARY_PALETTE = ["#2C7BE5", "#00D27A", "#F5803E", "#6E6CF5", "#17A2B8"]
FULL_PALETTE = [OOREDOO_RED, OOREDOO_DARK] + SECONDARY_PALETTE


def apply_card_layout(fig: go.Figure) -> go.Figure:
    """
    Applique le layout standard des cartes dashboard.
    
    Args:
        fig: Figure Plotly
    
    Returns:
        Figure avec layout appliqué
    """
    fig.update_layout(
        title=None,
        title_text="",  # Force empty title
        font=dict(family="Inter, system-ui, -apple-system, sans-serif", size=12, color="#1a1a1a"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )
    return fig


def build_daily_trend_chart(daily_mean: pd.DataFrame) -> go.Figure:
    """
    Graphique de tendance des scores avec markers et légère zone remplie.
    
    Args:
        daily_mean: DataFrame avec colonnes 'date_execution' et 'score_global_display'
    
    Returns:
        Figure Plotly
    """
    if daily_mean.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    fig = go.Figure()
    
    # Ligne avec markers
    fig.add_trace(go.Scatter(
        x=daily_mean["date_execution"],
        y=daily_mean["score_global_display"],
        mode='lines+markers',
        name='Score moyen',
        line=dict(color=OOREDOO_RED, width=3),
        marker=dict(size=8, color=OOREDOO_RED, line=dict(width=2, color='white')),
        fill='tozeroy',
        fillcolor=f'rgba(237, 28, 36, 0.1)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Score: %{y:.1%}<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Score moyen",
        yaxis=dict(
            tickformat='.0%',
            range=[0, 1],
            gridcolor='#EAECEF'
        ),
        xaxis=dict(gridcolor='#EAECEF'),
        hovermode='x unified'
    )
    
    apply_card_layout(fig)
    
    return fig


def build_execution_donut_chart(summary_model: pd.DataFrame, filtered: pd.DataFrame) -> go.Figure:
    """
    Donut chart de la répartition des exécutions par modèle.
    
    Args:
        summary_model: DataFrame résumé par modèle
        filtered: DataFrame des exécutions filtrées
    
    Returns:
        Figure Plotly
    """
    if filtered.empty or summary_model.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Compter les exécutions par modèle
    exec_counts = filtered.groupby("modele_nom").size().reset_index(name='count')
    exec_counts = exec_counts.sort_values('count', ascending=False)
    
    total = exec_counts['count'].sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=exec_counts['modele_nom'],
        values=exec_counts['count'],
        hole=0.6,
        marker=dict(colors=FULL_PALETTE),
        textinfo='label+percent',
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{value} exécutions<br>%{percent}<extra></extra>'
    )])
    
    # Ajouter le total au centre
    fig.add_annotation(
        text=f'<b>{total}</b><br>exécutions',
        x=0.5,
        y=0.5,
        font=dict(size=20, color="#1a1a1a"),
        showarrow=False
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.1
        )
    )
    
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=100, t=20, b=20))
    
    return fig


def build_ragas_grouped_bars(summary_model: pd.DataFrame, palette: str = "tableau10") -> go.Figure:
    """
    Barres horizontales groupées des 4 métriques RAGAS par modèle.
    
    Args:
        summary_model: DataFrame résumé par modèle
        palette: Nom de la palette de couleurs
    
    Returns:
        Figure Plotly
    """
    if summary_model.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Limiter aux top 10 modèles
    top_models = summary_model.head(10).copy()
    
    metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
    metric_labels = {
        'faithfulness': 'Faithfulness',
        'answer_relevancy': 'Answer Relevancy',
        'context_precision': 'Context Precision',
        'context_recall': 'Context Recall'
    }
    
    fig = go.Figure()
    
    colors = FULL_PALETTE
    
    for i, metric in enumerate(metrics):
        if metric in top_models.columns:
            fig.add_trace(go.Bar(
                name=metric_labels.get(metric, metric),
                x=top_models[metric],
                y=top_models['modele_nom'],
                orientation='h',
                marker=dict(color=colors[i % len(colors)]),
                hovertemplate='<b>%{y}</b><br>' + metric_labels.get(metric, metric) + ': %{x:.1%}<extra></extra>'
            ))
    
    fig.update_layout(
        barmode='group',
        xaxis_title="Score (0-1)",
        yaxis_title=None,
        xaxis=dict(
            tickformat='.0%',
            range=[0, 1],
            gridcolor='#EAECEF'
        ),
        yaxis=dict(autorange="reversed"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    return fig


def build_ragas_radar_chart(summary_model: pd.DataFrame) -> go.Figure:
    """
    Radar chart des 4 métriques RAGAS pour les top 5 modèles.
    Missing metrics = gap (pas de 0).
    
    Args:
        summary_model: DataFrame résumé par modèle
    
    Returns:
        Figure Plotly
    """
    if summary_model.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Limiter aux top 5 modèles
    top5 = summary_model.head(5).copy()
    
    metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
    metric_labels = ['Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall']
    
    fig = go.Figure()
    
    colors = FULL_PALETTE
    
    for i, (idx, row) in enumerate(top5.iterrows()):
        values = []
        for metric in metrics:
            val = row.get(metric)
            # Si NaN/None, on laisse None pour créer un gap
            values.append(val if pd.notna(val) else None)
        
        # Fermer le radar en ajoutant le premier point à la fin
        # Toujours fermer le polygone (même si values[0] est None)
        values_closed = values + [values[0]]
        labels_closed = metric_labels + [metric_labels[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill='toself',
            connectgaps=False,  # None = gap, jamais 0
            name=row['modele_nom'],
            marker=dict(color=colors[i % len(colors)]),
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='<b>%{theta}</b><br>%{r:.1%}<extra></extra>'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickformat='.0%',
                gridcolor='#EAECEF'
            ),
            angularaxis=dict(gridcolor='#EAECEF')
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.1
        )
    )
    
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=100, t=20, b=20))
    
    return fig


def build_latency_vs_score_scatter(filtered: pd.DataFrame) -> go.Figure:
    """
    Scatter plot latence vs score avec taille de bulle = nombre d'exécutions.
    
    Args:
        filtered: DataFrame des exécutions filtrées
    
    Returns:
        Figure Plotly
    """
    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Agréger par modèle
    model_agg = filtered.groupby('modele_nom').agg({
        'latence_secondes': 'mean',
        'score_global_display': 'mean',
        'execution_id': 'count'
    }).reset_index()
    model_agg.columns = ['modele_nom', 'latence_moyenne', 'score_moyen', 'nb_executions']
    
    # Filtrer les NaN
    model_agg = model_agg.dropna(subset=['latence_moyenne', 'score_moyen'])
    
    if model_agg.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Données insuffisantes pour le graphique",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        return fig
    
    fig = px.scatter(
        model_agg,
        x='latence_moyenne',
        y='score_moyen',
        size='nb_executions',
        text='modele_nom',
        color='modele_nom',
        color_discrete_sequence=FULL_PALETTE,
        size_max=60
    )
    
    fig.update_traces(
        textposition='top center',
        textfont=dict(size=10, color='#1a1a1a'),
        hovertemplate='<b>%{text}</b><br>Latence: %{x:.2f}s<br>Score: %{y:.1%}<br>Exécutions: %{marker.size}<extra></extra>'
    )
    
    fig.update_layout(
        xaxis_title="Latence moyenne (s)",
        yaxis_title="Score global moyen",
        yaxis=dict(tickformat='.0%', gridcolor='#EAECEF'),
        xaxis=dict(gridcolor='#EAECEF'),
        showlegend=False
    )
    
    apply_card_layout(fig)
    
    return fig


def build_scenario_ranking_chart(summary_scenario: pd.DataFrame) -> go.Figure:
    """
    Barres horizontales des top 10 scénarios avec gradient de couleur par score.
    
    Args:
        summary_scenario: DataFrame résumé par scénario
    
    Returns:
        Figure Plotly
    """
    if summary_scenario.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Top 10 scénarios
    top10 = summary_scenario.head(10).copy()
    top10 = top10.sort_values('score_global_display', ascending=True)  # Pour avoir les meilleurs en haut
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=top10['score_global_display'],
        y=top10['nom_cas_usage'],
        orientation='h',
        marker=dict(
            color=top10['score_global_display'],
            colorscale=[[0, '#F5803E'], [0.5, '#2C7BE5'], [1, '#00D27A']],
            showscale=True,
            colorbar=dict(
                title="Score",
                tickformat='.0%'
            )
        ),
        hovertemplate='<b>%{y}</b><br>Score: %{x:.1%}<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title="Score global",
        yaxis_title=None,
        xaxis=dict(
            tickformat='.0%',
            range=[0, 1],
            gridcolor='#EAECEF'
        ),
        height=400
    )
    
    apply_card_layout(fig)
    
    return fig


def build_scenario_ragas_grouped(summary_scenario: pd.DataFrame, palette: str = "tableau10") -> go.Figure:
    """
    Barres groupées des métriques RAGAS pour les top 10 scénarios.
    
    Args:
        summary_scenario: DataFrame résumé par scénario
        palette: Nom de la palette
    
    Returns:
        Figure Plotly
    """
    if summary_scenario.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Top 10 scénarios
    top10 = summary_scenario.head(10).copy()
    
    metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
    metric_labels = {
        'faithfulness': 'Faithfulness',
        'answer_relevancy': 'Answer Relevancy',
        'context_precision': 'Context Precision',
        'context_recall': 'Context Recall'
    }
    
    fig = go.Figure()
    
    colors = FULL_PALETTE
    
    for i, metric in enumerate(metrics):
        if metric in top10.columns:
            fig.add_trace(go.Bar(
                name=metric_labels.get(metric, metric),
                x=top10[metric],
                y=top10['nom_cas_usage'],
                orientation='h',
                marker=dict(color=colors[i % len(colors)]),
                hovertemplate='<b>%{y}</b><br>' + metric_labels.get(metric, metric) + ': %{x:.1%}<extra></extra>'
            ))
    
    fig.update_layout(
        barmode='group',
        xaxis_title="Score (0-1)",
        yaxis_title=None,
        xaxis=dict(
            tickformat='.0%',
            range=[0, 1],
            gridcolor='#EAECEF'
        ),
        yaxis=dict(autorange="reversed"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    return fig



def build_heatmap_chart(
    filtered: pd.DataFrame,
    summary_model: pd.DataFrame,
    summary_scenario: pd.DataFrame,
    view_mode: Literal["dept", "top15", "bottom15"],
    heat_order: str
) -> go.Figure:
    """
    Heatmap Plotly des scores (scénarios × modèles) avec options d'affichage.
    
    Args:
        filtered: DataFrame des exécutions filtrées
        summary_model: Résumé par modèle
        summary_scenario: Résumé par scénario
        view_mode: "dept" (agrégé par département), "top15", ou "bottom15"
        heat_order: "Moyenne modèle", "Moyenne scénario", ou "Aucun"
    
    Returns:
        Figure Plotly Heatmap
    """
    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Préparer la pivot table selon le mode
    if view_mode == "dept":
        # Agrégation par département
        pivot_data = (
            filtered.groupby(["departement", "modele_nom"])["score_global_display"]
            .mean()
            .reset_index()
            .pivot(index="departement", columns="modele_nom", values="score_global_display")
        )
        y_label = "Département"
    else:
        # Top 15 ou Bottom 15 scénarios
        if view_mode == "top15":
            scenarios = summary_scenario.head(15)["nom_cas_usage"].tolist()
        else:  # bottom15
            scenarios = summary_scenario.tail(15)["nom_cas_usage"].tolist()
        
        pivot_data = (
            filtered[filtered["nom_cas_usage"].isin(scenarios)]
            .pivot_table(index="nom_cas_usage", columns="modele_nom", values="score_global_display", aggfunc="mean")
        )
        y_label = "Scénario"
    
    if pivot_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Pas de données pour ce mode d'affichage",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    # Appliquer le tri
    if heat_order == "Moyenne modèle":
        # Trier colonnes par score moyen décroissant
        col_order = summary_model["modele_nom"].tolist()
        pivot_data = pivot_data[[col for col in col_order if col in pivot_data.columns]]
    elif heat_order == "Moyenne scénario" and view_mode != "dept":
        # Trier lignes par score moyen décroissant
        row_means = pivot_data.mean(axis=1).sort_values(ascending=False)
        pivot_data = pivot_data.loc[row_means.index]
    
    # Tronquer les noms de scénarios pour l'axe Y
    y_labels = []
    y_hover_labels = []
    for label in pivot_data.index:
        y_hover_labels.append(label)
        if len(label) > 40:
            y_labels.append(label[:37] + "...")
        else:
            y_labels.append(label)
    
    # Créer la heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=y_labels,
        customdata=np.array([[y_hover_labels[i]] * len(pivot_data.columns) for i in range(len(y_labels))]),
        colorscale=[
            [0, '#FDECEC'],      # Très clair (blanc/rose)
            [0.5, OOREDOO_RED],  # Rouge Ooredoo
            [1, OOREDOO_DARK]    # Rouge foncé
        ],
        zmin=0,
        zmax=1,
        hoverongaps=False,
        hovertemplate='<b>Modèle:</b> %{x}<br><b>' + y_label + ':</b> %{customdata[0]}<br><b>Score:</b> %{z:.1%}<extra></extra>',
        colorbar=dict(
            title="Score",
            tickformat='.0%',
            thickness=15,
            len=0.7
        ),
        xgap=2,
        ygap=2
    ))
    
    # Hauteur proportionnelle au nombre de lignes
    chart_height = min(600, max(300, len(pivot_data) * 28))
    
    fig.update_layout(
        xaxis_title="Modèle",
        yaxis_title=y_label,
        xaxis=dict(
            side='bottom',
            tickangle=-30 if len(pivot_data.columns) > 5 else 0
        ),
        yaxis=dict(autorange="reversed"),
        height=chart_height
    )
    
    apply_card_layout(fig)
    
    return fig


def build_score_histogram(filtered: pd.DataFrame) -> go.Figure:
    """
    Histogramme des scores globaux avec ligne de moyenne.
    
    Args:
        filtered: DataFrame des exécutions filtrées
    
    Returns:
        Figure Plotly
    """
    scores = filtered["score_global_display"].dropna()
    
    if scores.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Pas de données pour ce graphique",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig
    
    mean_score = scores.mean()
    
    fig = go.Figure()
    
    # Histogramme
    fig.add_trace(go.Histogram(
        x=scores,
        nbinsx=10,
        marker=dict(color=OOREDOO_RED, line=dict(color='white', width=1)),
        opacity=0.85,
        name='Distribution',
        hovertemplate='Score: %{x:.1%}<br>Nombre: %{y}<extra></extra>'
    ))
    
    # Ligne verticale pour la moyenne
    fig.add_vline(
        x=mean_score,
        line_dash="dash",
        line_color="#1a1a1a",
        line_width=2,
        annotation_text=f"Moyenne: {mean_score:.1%}",
        annotation_position="top right",
        annotation=dict(font=dict(size=11, color="#1a1a1a"))
    )
    
    fig.update_layout(
        xaxis_title="Score global",
        yaxis_title="Nombre d'exécutions",
        xaxis=dict(
            tickformat='.0%',
            range=[0, 1],
            gridcolor='#EAECEF'
        ),
        yaxis=dict(gridcolor='#EAECEF'),
        bargap=0.05,
        showlegend=False
    )
    
    apply_card_layout(fig)
    
    return fig


def build_latency_histogram(filtered: pd.DataFrame) -> tuple[go.Figure, Optional[str]]:
    """
    Histogramme des latences avec ligne de médiane et clipping des outliers.
    
    Args:
        filtered: DataFrame des exécutions filtrées
    
    Returns:
        Tuple (Figure Plotly, caption pour outliers ou None)
    """
    latencies = filtered["latence_secondes"].dropna()
    
    if latencies.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Pas de données pour ce graphique",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig, None
    
    median_latency = latencies.median()
    p95 = latencies.quantile(0.95)
    n_outliers = (latencies > p95).sum()
    
    # Filtrer pour l'affichage (garder <= p95)
    display_latencies = latencies[latencies <= p95]
    
    fig = go.Figure()
    
    # Histogramme
    fig.add_trace(go.Histogram(
        x=display_latencies,
        nbinsx=10,
        marker=dict(color="#2C7BE5", line=dict(color='white', width=1)),
        opacity=0.85,
        name='Distribution',
        hovertemplate='Latence: %{x:.2f}s<br>Nombre: %{y}<extra></extra>'
    ))
    
    # Ligne verticale pour la médiane
    fig.add_vline(
        x=median_latency,
        line_dash="dash",
        line_color="#1a1a1a",
        line_width=2,
        annotation_text=f"Médiane: {median_latency:.2f}s",
        annotation_position="top right",
        annotation=dict(font=dict(size=11, color="#1a1a1a"))
    )
    
    fig.update_layout(
        xaxis_title="Latence (s)",
        yaxis_title="Nombre d'exécutions",
        xaxis=dict(gridcolor='#EAECEF'),
        yaxis=dict(gridcolor='#EAECEF'),
        bargap=0.05,
        showlegend=False
    )
    
    apply_card_layout(fig)
    
    # Caption pour les outliers
    caption = None
    if n_outliers > 0:
        caption = f"⚠️ {n_outliers} exécution(s) > {p95:.1f}s non affichée(s)"
    
    return fig, caption


def build_scenario_top10_bar(summary_scenario: pd.DataFrame) -> go.Figure:
    """
    Clean horizontal bar chart of Top 10 scenarios by global score
    with Ooredoo branding colors and concise labels.

    Args:
        summary_scenario: DataFrame résumé par scénario (sorted desc by score)

    Returns:
        Figure Plotly
    """
    if summary_scenario.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig

    top10 = summary_scenario.head(10).copy()
    # Sort ascending so highest score is at top of horizontal bar chart
    top10 = top10.sort_values("score_global_display", ascending=True)

    # Truncate long scenario names for readability
    top10["label"] = top10["nom_cas_usage"].apply(
        lambda x: (x[:45] + "…") if len(x) > 45 else x
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top10["score_global_display"],
        y=top10["label"],
        orientation="h",
        marker=dict(
            color=top10["score_global_display"],
            colorscale=[
                [0, "#F5803E"],
                [0.5, OOREDOO_RED],
                [1, "#00D27A"],
            ],
            line=dict(width=0),
        ),
        text=top10["score_global_display"].apply(lambda v: f"{v:.1%}"),
        textposition="outside",
        textfont=dict(size=11, color="#1a1a1a"),
        hovertemplate=(
            "<b>%{customdata}</b><br>"
            "Score global : %{x:.1%}<extra></extra>"
        ),
        customdata=top10["nom_cas_usage"],  # full name in hover
    ))

    fig.update_layout(
        xaxis=dict(
            tickformat=".0%", range=[0, 1.12],
            gridcolor="#EAECEF", title=None,
        ),
        yaxis=dict(title=None),
        height=380,
    )
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=40, t=10, b=10))
    return fig


def build_scenario_ragas_top_grouped(
    summary_scenario: pd.DataFrame,
    top_n: int = 10,
) -> go.Figure:
    """
    Compact grouped horizontal bar chart showing the 4 RAGAS criteria
    for the Top N scenarios.  Fixed reasonable height for executive readability.

    Args:
        summary_scenario: DataFrame résumé par scénario (sorted desc)
        top_n: Number of scenarios to show (10 or 15)

    Returns:
        Figure Plotly
    """
    if summary_scenario.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune donnée disponible",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#6B7280")
        )
        apply_card_layout(fig)
        return fig

    top = summary_scenario.head(top_n).copy()

    # Truncate labels
    top["label"] = top["nom_cas_usage"].apply(
        lambda x: (x[:42] + "…") if len(x) > 42 else x
    )

    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    metric_labels = {
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer Relevancy",
        "context_precision": "Context Precision",
        "context_recall": "Context Recall",
    }
    colors = [OOREDOO_RED, "#2C7BE5", "#00D27A", "#F5803E"]

    fig = go.Figure()
    for i, metric in enumerate(metrics):
        if metric in top.columns:
            fig.add_trace(go.Bar(
                name=metric_labels.get(metric, metric),
                x=top[metric],
                y=top["label"],
                orientation="h",
                marker=dict(color=colors[i]),
                hovertemplate=(
                    "<b>%{customdata}</b><br>"
                    + metric_labels.get(metric, metric)
                    + " : %{x:.1%}<extra></extra>"
                ),
                customdata=top["nom_cas_usage"],
            ))

    bar_height = max(380, min(560, top_n * 38))
    fig.update_layout(
        barmode="group",
        xaxis=dict(
            tickformat=".0%", range=[0, 1],
            gridcolor="#EAECEF", title=None,
        ),
        yaxis=dict(autorange="reversed", title=None),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        height=bar_height,
    )
    apply_card_layout(fig)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=10))
    return fig
