from sqlalchemy import text
from src.database.connection import engine
from src.rag.embeddings import get_embedding
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def init_vector_table():
    """Initialize the vector table with pgvector extension."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS documents_vectorises (
                    id SERIAL PRIMARY KEY,
                    departement VARCHAR NOT NULL,
                    contenu TEXT NOT NULL,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_departement 
                ON documents_vectorises(departement);
            """))
            conn.commit()
            logger.info("Vector table initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector table: {str(e)}")
        raise

def add_document_chunk(departement: str, contenu: str):
    """Add a document chunk with its embedding to the vector store."""
    try:
        embedding = get_embedding(contenu)
        
        # Proper pgvector format: array as string '[1.0, 2.0, ...]'
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO documents_vectorises (departement, contenu, embedding)
                    VALUES (:departement, :contenu, :embedding::vector)
                """),
                {
                    "departement": departement, 
                    "contenu": contenu, 
                    "embedding": embedding_str
                }
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to add document chunk: {str(e)}")
        raise

def search_similar(query: str, departement: str, top_k: int = 3):
    """Search for similar chunks using semantic similarity."""
    try:
        query_embedding = get_embedding(query)
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT contenu, embedding <-> :embedding::vector AS distance
                    FROM documents_vectorises
                    WHERE departement = :departement
                    ORDER BY distance ASC
                    LIMIT :top_k
                """),
                {
                    "embedding": embedding_str, 
                    "departement": departement, 
                    "top_k": top_k
                }
            )
            chunks = [row[0] for row in result]
            logger.debug(f"Retrieved {len(chunks)} similar chunks for departement={departement}")
            return chunks
    except Exception as e:
        logger.error(f"Search failed for departement={departement}: {str(e)}")
        raise