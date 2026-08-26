"""
Error handling utilities for Streamlit dashboard modules.

This module provides decorators and utilities for consistent error handling
across all dashboard components.
"""

import streamlit as st
import functools
from typing import Callable, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def handle_dashboard_errors(func: Callable) -> Callable:
    """
    Decorator for dashboard functions to provide consistent error handling.
    
    Shows user-friendly error messages while logging detailed error information.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # User-friendly error display
            st.error(f"Erreur dans {func.__name__.replace('_', ' ').title()}")
            
            # Show details in expandable section
            with st.expander("Détails de l'erreur (pour le débogage)"):
                st.exception(e)
                
            # Offer recovery options
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Réessayer", key=f"retry_{func.__name__}"):
                    st.rerun()
                    
            with col2:
                if st.button("Vider le cache", key=f"clear_cache_{func.__name__}"):
                    st.cache_data.clear()
                    st.success("Cache vidé")
                    
            return None
            
    return wrapper

def safe_data_operation(operation_name: str, operation_func: Callable, *args, **kwargs) -> Any:
    """
    Safely execute a data operation with error handling and user feedback.
    
    Args:
        operation_name: Human-readable name for the operation
        operation_func: Function to execute
        *args, **kwargs: Arguments for the function
        
    Returns:
        Result of the operation or None if failed
    """
    try:
        logger.debug(f"Executing data operation: {operation_name}")
        result = operation_func(*args, **kwargs)
        logger.debug(f"Data operation successful: {operation_name}")
        return result
        
    except Exception as e:
        logger.error(f"Data operation failed ({operation_name}): {e}", exc_info=True)
        
        st.error(f"Erreur lors de l'opération : {operation_name}")
        
        with st.expander("Détails de l'erreur"):
            st.write(f"**Opération:** {operation_name}")
            st.write(f"**Erreur:** {str(e)}")
            st.exception(e)
            
        return None

def show_data_loading_error(operation_name: str, error: Exception):
    """Show a standardized error message for data loading failures."""
    logger.error(f"Data loading error ({operation_name}): {error}", exc_info=True)
    
    st.error(f"Impossible de charger les données : {operation_name}")
    
    # Show helpful suggestions
    st.info("**Suggestions :**")
    st.write("- Vérifiez votre connexion à la base de données")
    st.write("- Contactez votre administrateur si le problème persiste")
    st.write("- Essayez de vider le cache et de recharger la page")
    
    with st.expander("Détails techniques"):
        st.exception(error)

def show_empty_data_message(data_type: str, suggestions: list = None):
    """Show a standardized message when no data is available."""
    logger.info(f"No data available for: {data_type}")
    
    st.info(f"Aucune donnée disponible : {data_type}")
    
    if suggestions:
        st.write("**Suggestions :**")
        for suggestion in suggestions:
            st.write(f"- {suggestion}")
    else:
        st.write("**Suggestions :**")
        st.write("- Vérifiez que des données ont été créées dans le système")
        st.write("- Contactez votre administrateur pour plus d'informations")

def with_loading_spinner(message: str = "Chargement en cours..."):
    """Context manager to show loading spinner with custom message."""
    return st.spinner(message)

class DashboardErrorHandler:
    """Context manager for comprehensive error handling in dashboard sections."""
    
    def __init__(self, section_name: str, show_errors: bool = True):
        self.section_name = section_name
        self.show_errors = show_errors
        
    def __enter__(self):
        logger.debug(f"Entering dashboard section: {self.section_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(
                f"Error in dashboard section '{self.section_name}': {exc_val}", 
                exc_info=True
            )
            
            if self.show_errors:
                st.error(f"Erreur dans la section : {self.section_name}")
                
                with st.expander("Détails de l'erreur"):
                    st.exception(exc_val)
                    
                if st.button(f"Réessayer {self.section_name}", key=f"retry_{self.section_name}"):
                    st.rerun()
                    
            return True  # Suppress the exception
        
        logger.debug(f"Dashboard section completed successfully: {self.section_name}")
        return False

# Utility function for safe metric display
def safe_metric(label: str, value, delta=None, key=None):
    """Display a metric with error handling for invalid values."""
    try:
        if value is None or (hasattr(value, '__len__') and len(value) == 0):
            st.metric(label, "N/A", delta=delta, key=key)
        else:
            st.metric(label, value, delta=delta, key=key)
    except Exception as e:
        logger.warning(f"Error displaying metric '{label}': {e}")
        st.metric(label, "Erreur", key=key)

# Utility function for safe dataframe display
def safe_dataframe(df, key=None, **kwargs):
    """Display a dataframe with error handling."""
    try:
        if df is None or df.empty:
            st.info("Aucune donnée à afficher")
            return
        st.dataframe(df, key=key, **kwargs)
    except Exception as e:
        logger.error(f"Error displaying dataframe: {e}", exc_info=True)
        st.error("Erreur lors de l'affichage des données")
        with st.expander("Détails"):
            st.exception(e)