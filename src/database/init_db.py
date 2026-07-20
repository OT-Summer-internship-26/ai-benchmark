from sqlalchemy import create_engine
from src.database.models import Base
from src.config.settings import DATABASE_URL

def init_database():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    print("Base de données initialisée avec succès.")

if __name__ == "__main__":
    init_database()