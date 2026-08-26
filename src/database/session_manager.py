"""
Database session management utilities for ensuring proper session cleanup.

This module provides decorators and context managers to ensure database sessions
are always properly closed, even in case of exceptions.
"""

from contextlib import contextmanager
from functools import wraps
from typing import Callable, Any
from src.database.connection import SessionLocal
import logging

logger = logging.getLogger(__name__)

@contextmanager
def db_session():
    """Context manager for database sessions with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def with_db_session(func: Callable) -> Callable:
    """
    Decorator that provides a database session as the first argument to a function.
    
    Usage:
        @with_db_session
        def my_function(db, arg1, arg2):
            # db is automatically provided
            return db.query(Model).all()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with db_session() as db:
            return func(db, *args, **kwargs)
    return wrapper

def safe_execute(operation: Callable, *args, **kwargs) -> Any:
    """
    Safely execute a database operation with automatic session management.
    
    Args:
        operation: Function that takes db as first argument
        *args, **kwargs: Arguments to pass to the operation
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: If the operation fails after cleanup
    """
    with db_session() as db:
        return operation(db, *args, **kwargs)

class DatabaseTransaction:
    """Context manager for explicit database transactions."""
    
    def __init__(self):
        self.session = None
        
    def __enter__(self):
        self.session = SessionLocal()
        return self.session
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
                logger.error(f"Transaction rolled back due to: {exc_val}")
        finally:
            self.session.close()

# Example usage functions for common patterns
def query_with_session(query_func: Callable, *args, **kwargs):
    """Execute a query function with proper session management."""
    return safe_execute(query_func, *args, **kwargs)

def update_with_session(update_func: Callable, *args, **kwargs):
    """Execute an update function with proper session management."""
    return safe_execute(update_func, *args, **kwargs)

def create_with_session(create_func: Callable, *args, **kwargs):
    """Execute a create function with proper session management."""
    return safe_execute(create_func, *args, **kwargs)

def delete_with_session(delete_func: Callable, *args, **kwargs):
    """Execute a delete function with proper session management."""
    return safe_execute(delete_func, *args, **kwargs)