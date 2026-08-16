from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.settings import DATABASE_URL
import os

# Create engine and session directly but with error handling
try:
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please check your .env file and ensure DATABASE_URL is configured."
        )
    
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"WARNING: Failed to initialize database engine: {e}")
    print(f"DATABASE_URL = {DATABASE_URL}")
    raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()