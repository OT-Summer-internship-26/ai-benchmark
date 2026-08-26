from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from src.config.settings import DATABASE_URL
import os
import logging

# Set up logging for database connections
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

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
        pool_timeout=30,  # Add timeout for getting connections
        connect_args={
            "options": "-c timezone=UTC",  # Set timezone
            "connect_timeout": 10,  # Connection timeout
        }
    )
    
    # Add connection event listener for monitoring
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set connection-specific settings on connect."""
        # This would apply to PostgreSQL connections
        pass
    
    @event.listens_for(Engine, "checkout")  
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Monitor connection checkout."""
        pass
    
    @event.listens_for(Engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        """Monitor connection checkin."""
        pass
    
    SessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine,
        expire_on_commit=False  # Keep objects accessible after commit
    )
    
    # Test the connection
    with engine.connect() as test_conn:
        test_conn.execute(text("SELECT 1"))
        
except Exception as e:
    print(f"CRITICAL: Failed to initialize database engine: {e}")
    print(f"DATABASE_URL = {DATABASE_URL}")
    raise

def get_db():
    """Dependency injection for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Get a database session with automatic cleanup."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise

def safe_db_operation(operation_func, *args, **kwargs):
    """
    Execute a database operation with automatic session management.
    
    Args:
        operation_func: Function that takes db as first argument
        *args, **kwargs: Additional arguments for the function
        
    Returns:
        Result of the operation or None if failed
    """
    db = SessionLocal()
    try:
        return operation_func(db, *args, **kwargs)
    except Exception as e:
        db.rollback()
        print(f"Database operation failed: {e}")
        raise
    finally:
        db.close()

# Health check function
def check_database_health():
    """Check if database is accessible and responsive."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False

# Connection pool status
def get_pool_status():
    """Get current connection pool status for monitoring."""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow()
    }