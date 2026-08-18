"""
Radar chart data for multi-metric comparison across models in a department.

Provides data structure for radar visualization showing model performance across 4 Ragas metrics.
"""

import pandas as pd
from src.dashboard.admin_queries import get_department_model_comparison


def get_radar_chart_data(department: str, max_models: int = 6) -> dict | None:
    """
    Get radar chart data for comparing model metrics for a department.
    
    Shows all models tested in the department, with 4 Ragas metrics as axes:
    - Faithfulness
    - Answer Relevancy
    - Context Precision
    - Context Recall
    
    Args:
        department: Department name
        max_models: Maximum models to display (limits chart clutter)
        
    Returns:
        Dict with radar data or None if no data
        {
            "department": str,
            "models": [
                {
                    "name": str,
                    "metrics": {
                        "faithfulness": float,
                        "answer_relevancy": float,
                        "context_precision": float,
                        "context_recall": float,
                    },
                    "global_score": float,
                    "execution_count": int,
                    "avg_latency": float
                },
                ...
            ]
        }
    """
    
    df = get_department_model_comparison(department)
    
    if df.empty:
        return None
    
    # Limit to top models by global score
    df = df.head(max_models)
    
    models_data = []
    for idx, row in df.iterrows():
        models_data.append({
            "name": row['model_name'],
            "metrics": {
                "faithfulness": float(row['faithfulness']) if row['faithfulness'] else 0.0,
                "answer_relevancy": float(row['answer_relevancy']) if row['answer_relevancy'] else 0.0,
                "context_precision": float(row['context_precision']) if row['context_precision'] else 0.0,
                "context_recall": float(row['context_recall']) if row['context_recall'] else 0.0,
            },
            "global_score": float(row['global_score']),
            "execution_count": int(row['execution_count']),
            "avg_latency": float(row['avg_latency']) if row['avg_latency'] else None,
        })
    
    return {
        "department": department,
        "models": models_data,
    }


def create_metrics_comparison_table(department: str) -> pd.DataFrame | None:
    """
    Create a data table with detailed metrics for all models in a department.
    
    Args:
        department: Department name
        
    Returns:
        DataFrame with model metrics or None if no data
    """
    
    df = get_department_model_comparison(department)
    
    if df.empty:
        return None
    
    # Select relevant columns and format
    display_df = df[[
        'model_name',
        'faithfulness',
        'answer_relevancy',
        'context_precision',
        'context_recall',
        'global_score',
        'avg_latency',
        'execution_count',
    ]].copy()
    
    # Rename for display
    display_df.columns = [
        'Model',
        'Faithfulness',
        'Answer Relevancy',
        'Context Precision',
        'Context Recall',
        'Global Score',
        'Avg Latency (s)',
        'Executions',
    ]
    
    # Format percentages
    for col in ['Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall', 'Global Score']:
        display_df[col] = display_df[col].apply(lambda x: f'{x:.1%}' if pd.notna(x) else 'N/A')
    
    # Format latency
    display_df['Avg Latency (s)'] = display_df['Avg Latency (s)'].apply(
        lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A'
    )
    
    return display_df.reset_index(drop=True)
