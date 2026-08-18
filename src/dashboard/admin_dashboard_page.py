#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin Dashboard Page - Streamlit UI for admin view enhancements

Features:
1. Department filter with cascading to scenarios/models
2. Radar chart for multi-metric model comparison
3. Per-department leaderboard
4. Metrics comparison table
"""

import sys
import pathlib

# ---------------------------------------------------------------------------
# Path bootstrap — ensures `src` is importable when running:
#   streamlit run src/dashboard/admin_dashboard_page.py
# This resolves to the project root (2 levels up from this file).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.admin_queries import (
    get_all_departments,
    get_scenarios_for_departments,
    get_models_for_departments,
    get_department_leaderboard,
)
from src.dashboard.radar_chart import (
    get_radar_chart_data,
    create_metrics_comparison_table,
)


def render_admin_dashboard():
    """Main admin dashboard page."""
    
    st.set_page_config(
        page_title="Admin Dashboard - Ooredoo IA Benchmark",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.title("⚙️ Admin Dashboard - Model Benchmark Analysis")
    st.markdown("Department-level analysis with cascading filters, model comparison, and performance ranking.")
    
    # ========================================================================
    # SIDEBAR: Department Filter (Cascading)
    # ========================================================================
    
    with st.sidebar:
        st.header("Filters")
        
        # Load all departments
        all_depts = get_all_departments()
        dept_names = [d["name"] for d in all_depts]
        dept_display = [f"{d['name']} ({d['execution_count']} exec)" for d in all_depts]
        
        # Multi-select departments
        selected_dept_display = st.multiselect(
            "Select Departments",
            dept_display,
            default=dept_display,
            help="Choose one or more departments to filter views"
        )
        
        # Extract department names from display
        selected_depts = [
            dept_names[dept_display.index(d)]
            for d in selected_dept_display
            if d in dept_display
        ]
        
        if not selected_depts:
            st.warning("Please select at least one department")
            return
        
        # Cascading: Get scenarios and models for selected departments
        scenarios = get_scenarios_for_departments(selected_depts)
        models = get_models_for_departments(selected_depts)

        scenario_labels = {
            scenario["id"]: f"{scenario['departement']} — {scenario['nom_cas_usage']}"
            for scenario in scenarios
        }
        selected_scenario_ids = st.multiselect(
            "Scénarios",
            options=list(scenario_labels),
            default=list(scenario_labels),
            format_func=lambda scenario_id: scenario_labels[scenario_id],
            help="Le catalogue est lu directement depuis la table scenarios, y compris sans score.",
        )
        visible_scenarios = [
            scenario for scenario in scenarios if scenario["id"] in selected_scenario_ids
        ]
        
        st.markdown("---")
        st.subheader("Cascading Data")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Scenarios", len(visible_scenarios))
        with col2:
            st.metric("Models Tested", f"{len(models)} / 12")
        
        st.caption("📊 Note: 4 of 12 models have benchmark data (8 remote models pending benchmarking)")
    
    # ========================================================================
    # MAIN CONTENT: Department Overview
    # ========================================================================
    
    st.header("📊 Department Overview")
    
    # Show selected departments summary
    dept_summary_cols = st.columns(len(selected_depts))
    for idx, dept_name in enumerate(selected_depts):
        dept_info = next((d for d in all_depts if d["name"] == dept_name), None)
        if dept_info:
            with dept_summary_cols[idx]:
                st.metric(
                    dept_name,
                    f"{dept_info['execution_count']} exec",
                    f"{dept_info['scenario_count']} scenarios"
                )
    
    st.markdown("---")

    scenario_coverage = pd.DataFrame(visible_scenarios)
    
    # ========================================================================
    # TAB 1: Leaderboard
    # ========================================================================
    
    tab_leaderboard, tab_radar, tab_table, tab_data = st.tabs([
        "🏆 Leaderboard",
        "📈 Radar Chart",
        "📋 Metrics Table",
        "🔍 Raw Data"
    ])
    
    with tab_leaderboard:
        st.subheader("Model Ranking by Department")

        st.markdown("#### Couverture des scénarios")
        if not scenario_coverage.empty:
            st.dataframe(
                scenario_coverage[
                    ["departement", "nom_cas_usage", "data_status"]
                ].rename(
                    columns={
                        "departement": "Département",
                        "nom_cas_usage": "Scénario",
                        "data_status": "État",
                    }
                ),
                hide_index=True,
            )
        else:
            st.info("Aucun scénario sélectionné.")
        
        leaderboard_df = get_department_leaderboard(selected_depts)
        
        if leaderboard_df.empty:
            st.info("No benchmark data available for selected departments.")
        else:
            # Group by department
            for dept_name in selected_depts:
                dept_lb = leaderboard_df[leaderboard_df['departement'] == dept_name]
                
                if dept_lb.empty:
                    st.info(f"No data for {dept_name}")
                    continue
                
                st.subheader(dept_name)
                
                # Format leaderboard display
                display_df = dept_lb[[
                    'rank', 'model_name', 'global_score', 'execution_count',
                    'faithfulness', 'answer_relevancy', 'context_precision', 'context_recall'
                ]].copy()
                
                display_df.columns = [
                    'Rank', 'Model', 'Global Score', 'Executions',
                    'Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall'
                ]
                
                # Format numeric columns
                display_df['Global Score'] = display_df['Global Score'].apply(lambda x: f'{x:.1%}')
                display_df['Faithfulness'] = display_df['Faithfulness'].apply(lambda x: f'{x:.1%}' if pd.notna(x) else 'N/A')
                display_df['Answer Relevancy'] = display_df['Answer Relevancy'].apply(lambda x: f'{x:.1%}' if pd.notna(x) else 'N/A')
                display_df['Context Precision'] = display_df['Context Precision'].apply(lambda x: f'{x:.1%}' if pd.notna(x) else 'N/A')
                display_df['Context Recall'] = display_df['Context Recall'].apply(lambda x: f'{x:.1%}' if pd.notna(x) else 'N/A')
                
                # Highlight top 3
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                )
                
                st.markdown("---")
    
    # ========================================================================
    # TAB 2: Radar Chart
    # ========================================================================
    
    with tab_radar:
        st.subheader("Multi-Metric Model Comparison (Radar Chart)")
        
        # If single department selected, show radar
        if len(selected_depts) == 1:
            dept_name = selected_depts[0]
            radar_data = get_radar_chart_data(dept_name)
            
            if radar_data and radar_data["models"]:
                # Create Plotly radar chart
                fig = go.Figure()
                
                colors = [
                    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'
                ]
                
                for idx, model in enumerate(radar_data["models"]):
                    metrics = model["metrics"]
                    values = [
                        metrics["faithfulness"],
                        metrics["answer_relevancy"],
                        metrics["context_precision"],
                        metrics["context_recall"],
                    ]
                    
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=['Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall'],
                        fill='toself',
                        name=model['name'],
                        line=dict(color=colors[idx % len(colors)]),
                        fillcolor=colors[idx % len(colors)],
                        opacity=0.6,
                    ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1.0],
                            tickformat='.0%',
                        ),
                    ),
                    showlegend=True,
                    title=dict(
                        text=f"Model Comparison: {dept_name}",
                        font=dict(size=16),
                    ),
                    font=dict(size=11),
                    height=600,
                    hovermode='closest',
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No metric data available for {dept_name}")
        else:
            st.info("Radar chart displays one department at a time. Please select a single department.")
    
    # ========================================================================
    # TAB 3: Metrics Table
    # ========================================================================
    
    with tab_table:
        st.subheader("Detailed Metrics Comparison")
        
        if len(selected_depts) == 1:
            dept_name = selected_depts[0]
            table_df = create_metrics_comparison_table(dept_name)
            
            if table_df is not None and not table_df.empty:
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(f"No metrics available for {dept_name}")
        else:
            st.info("Metrics table displays one department at a time. Please select a single department.")
    
    # ========================================================================
    # TAB 4: Raw Data
    # ========================================================================
    
    with tab_data:
        st.subheader("Raw Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Scenarios")
            if visible_scenarios:
                scenarios_df = pd.DataFrame(visible_scenarios)
                st.dataframe(scenarios_df, hide_index=True)
            else:
                st.info("No scenarios found")
        
        with col2:
            st.subheader("Models")
            if models:
                models_df = pd.DataFrame(models)
                st.dataframe(models_df, use_container_width=True)
            else:
                st.info("No models found")
        
        st.subheader("Complete Leaderboard")
        leaderboard_df = get_department_leaderboard(selected_depts)
        if not leaderboard_df.empty:
            st.dataframe(leaderboard_df, use_container_width=True)
        else:
            st.info("No leaderboard data")


if __name__ == "__main__":
    render_admin_dashboard()
