from src.database.connection import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        db_info = conn.execute(text(
            "SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"
        ))
        print("Connexion actuelle :", db_info.fetchone())

        try:
            count = conn.execute(text("SELECT COUNT(*) FROM documents_vectorises"))
            print("Nombre de chunks dans documents_vectorises :", count.scalar())
        except Exception as e:
            print("Erreur en comptant documents_vectorises :", e)

        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ))
        print("Tables visibles :", [t[0] for t in tables])