"""
Centralized formatting utilities for dashboard displays.

Ensures consistent handling of None/NaN values across all dashboard pages,
preventing TypeError when displaying metrics with missing data.

All formatting functions return "N/A" (or custom default_text) for None/NaN values
instead of crashing with unsupported format string errors.
"""

import pandas as pd


def safe_format_score(value, as_percentage=True, default_text="N/A"):
    """
    Safely format score values, handling None, NaN, and numeric values.
    
    Args:
        value: Score value to format (float, None, or NaN)
        as_percentage: If True, format as percentage (e.g., "75.3%")
                      If False, format as decimal (e.g., "0.75")
        default_text: Text to display for None/NaN values (default: "N/A")
        
    Returns:
        Formatted string or default_text
        
    Examples:
        >>> safe_format_score(0.753, as_percentage=True)
        '75.3%'
        >>> safe_format_score(None)
        'N/A'
        >>> safe_format_score(float('nan'), default_text="—")
        '—'
    """
    if value is None or pd.isna(value):
        return default_text
    
    try:
        if as_percentage:
            return f"{float(value):.1%}"
        else:
            return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return default_text


def safe_format_cost(value, default_text="N/A"):
    """
    Safely format cost values with $ suffix.
    
    Args:
        value: Cost value to format (float, None, or NaN)
        default_text: Text to display for None/NaN values (default: "N/A")
        
    Returns:
        Formatted string with 4 decimal places or default_text
        
    Examples:
        >>> safe_format_cost(0.0012)
        '0.0012 $'
        >>> safe_format_cost(None)
        'N/A'
    """
    if value is None or pd.isna(value):
        return default_text
    
    try:
        return f"{float(value):.4f} $"
    except (ValueError, TypeError):
        return default_text


def safe_format_latency(value, default_text="N/A"):
    """
    Safely format latency values with seconds suffix.
    
    Args:
        value: Latency value in seconds (float, None, or NaN)
        default_text: Text to display for None/NaN values (default: "N/A")
        
    Returns:
        Formatted string with 2 decimal places or default_text
        
    Examples:
        >>> safe_format_latency(1.234)
        '1.23 s'
        >>> safe_format_latency(None)
        'N/A'
    """
    if value is None or pd.isna(value):
        return default_text
    
    try:
        return f"{float(value):.2f} s"
    except (ValueError, TypeError):
        return default_text


def safe_format_metrics_dict(metrics: dict, default_text="N/A") -> dict:
    """
    Format all metrics in a dictionary, replacing None with default_text.
    
    Useful for formatting radar chart data or metric comparison tables.
    
    Args:
        metrics: Dictionary of metric_name -> value
        default_text: Text to display for None/NaN values (default: "N/A")
        
    Returns:
        Dictionary with all values formatted as percentage strings
        
    Examples:
        >>> safe_format_metrics_dict({
        ...     'faithfulness': 0.85,
        ...     'context_recall': None,
        ...     'answer_relevancy': 0.72
        ... })
        {'faithfulness': '85.0%', 'context_recall': 'N/A', 'answer_relevancy': '72.0%'}
    """
    return {
        key: safe_format_score(val, as_percentage=True, default_text=default_text)
        for key, val in metrics.items()
    }


def safe_float_for_plotly(value, fallback=0.0):
    """
    Convert value to float for Plotly charts, with fallback for None/NaN.
    
    Plotly radar charts require numeric values. This function converts None/NaN
    to a numeric fallback (default 0.0) instead of breaking the chart.
    
    Args:
        value: Value to convert (float, None, or NaN)
        fallback: Numeric value to use for None/NaN (default: 0.0)
        
    Returns:
        Float value or fallback
        
    Examples:
        >>> safe_float_for_plotly(0.85)
        0.85
        >>> safe_float_for_plotly(None)
        0.0
        >>> safe_float_for_plotly(None, fallback=-1.0)
        -1.0
    """
    if value is None or pd.isna(value):
        return fallback
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return fallback
