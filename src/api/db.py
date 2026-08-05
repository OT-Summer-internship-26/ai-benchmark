"""
Connexion PostgreSQL pour l'API FastAPI.

On réutilise l'engine SQLAlchemy déjà configuré dans src/database/connection.py
(le même que celui utilisé par src/rag/vector_store.py) — pas de duplication,
pas de deuxième système de connexion.
"""

from src.database.connection import engine

__all__ = ["engine"]