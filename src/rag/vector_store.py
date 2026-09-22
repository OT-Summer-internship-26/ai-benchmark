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
                    VALUES (:departement, :contenu, CAST(:embedding AS vector))
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

DEPARTMENT_ALIASES = {
    "rh": "RH",
    "rh & communication": "RH",
    "ressources humaines": "RH",
    "it": "IT & Cybersécurité",
    "it & architecture": "IT & Cybersécurité",
    "it & cybersécurité": "IT & Cybersécurité",
    "it & cybersecurite": "IT & Cybersécurité",
    "noc": "IT & Cybersécurité",
    "réseau": "IT & Cybersécurité",
    "reseau": "IT & Cybersécurité",
    "support noc": "IT & Cybersécurité",
    "marketing": "Marketing & Digital",
    "marketing & digital": "Marketing & Digital",
    "productivité": "Productivité & Transversal",
    "productivite": "Productivité & Transversal",
    "productivité personnelle": "Productivité & Transversal",
    "productivite personnelle": "Productivité & Transversal",
    "productivité & transversal": "Productivité & Transversal",
    "productivite & transversal": "Productivité & Transversal",
    "service client": "Service Client",
}


def search_similar(query: str, departement: str, top_k: int = 3):
    """Search for similar chunks using semantic similarity with department fallback matching."""
    try:
        query_embedding = get_embedding(query)
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Normalize department using aliases
        normalized_dept = DEPARTMENT_ALIASES.get(departement.strip().lower(), departement)
        
        with engine.connect() as conn:
            # 1. First attempt: exact match or normalized match
            result = conn.execute(
                text("""
                    SELECT contenu, embedding <-> CAST(:embedding AS vector) AS distance
                    FROM documents_vectorises
                    WHERE departement = :departement OR departement = :normalized_dept
                    ORDER BY distance ASC
                    LIMIT :top_k
                """),
                {
                    "embedding": embedding_str, 
                    "departement": departement,
                    "normalized_dept": normalized_dept,
                    "top_k": top_k
                }
            )
            chunks = [row[0] for row in result]
            
            # 2. Fallback: case-insensitive partial ILIKE match if no chunks found
            if not chunks:
                search_term = f"%{departement.split('&')[0].strip()}%"
                result = conn.execute(
                    text("""
                        SELECT contenu, embedding <-> CAST(:embedding AS vector) AS distance
                        FROM documents_vectorises
                        WHERE departement ILIKE :search_term
                        ORDER BY distance ASC
                        LIMIT :top_k
                    """),
                    {
                        "embedding": embedding_str,
                        "search_term": search_term,
                        "top_k": top_k
                    }
                )
                chunks = [row[0] for row in result]

            logger.debug(f"Retrieved {len(chunks)} similar chunks for departement='{departement}'")
            return chunks
    except Exception as e:
        logger.error(f"Search failed for departement={departement}: {str(e)}")
        raise