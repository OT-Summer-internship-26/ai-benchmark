from sqlalchemy import text
from src.database.connection import engine
from src.rag.embeddings import get_embedding

def init_vector_table():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents_vectorises (
                id SERIAL PRIMARY KEY,
                departement VARCHAR NOT NULL,
                contenu TEXT NOT NULL,
                embedding vector(384)
            );
        """))
        conn.commit()
    print("Table vectorielle initialisée.")

def add_document_chunk(departement: str, contenu: str):
    embedding = get_embedding(contenu)
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO documents_vectorises (departement, contenu, embedding)
                VALUES (:departement, :contenu, :embedding)
            """),
            {"departement": departement, "contenu": contenu, "embedding": str(embedding)}
        )
        conn.commit()

def search_similar(query: str, departement: str, top_k: int = 3):
    query_embedding = get_embedding(query)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT contenu, embedding <-> CAST(:embedding AS vector) AS distance
                FROM documents_vectorises
                WHERE departement = :departement
                ORDER BY distance ASC
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "departement": departement, "top_k": top_k}
        )
        return [row[0] for row in result]