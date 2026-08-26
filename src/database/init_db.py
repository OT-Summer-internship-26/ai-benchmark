import sys
import pathlib

# Add project root to path
project_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from src.database.models import Base, Utilisateur, Scenario, Modele
from src.config.settings import DATABASE_URL
from src.auth.utils import hash_password
from src.database.connection import SessionLocal

def init_database():
    """Initialize database with tables and basic data."""
    print("=" * 80)
    print("INITIALIZING OOREDOO IA BENCHMARK DATABASE")
    print("=" * 80)
    
    try:
        # Create engine and tables
        engine = create_engine(DATABASE_URL)
        print("✅ Connecting to database...")
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Create all tables
        print("✅ Creating database tables...")
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully")
        
        # Add test users
        create_test_users()
        
        # Add sample models
        create_sample_models()
        
        # Add sample scenarios
        create_sample_scenarios()
        
        print("\n" + "=" * 80)
        print("DATABASE INITIALIZATION COMPLETE")
        print("=" * 80)
        print("\nTest login credentials:")
        print("  - client@ooredoo.com / client123 (Client)")
        print("  - admin@ooredoo.com / admin123 (Admin)")
        print("  - superadmin@ooredoo.com / superadmin123 (Super Admin)")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def create_test_users():
    """Create test user accounts for all roles."""
    print("✅ Creating test user accounts...")
    
    db = SessionLocal()
    try:
        test_accounts = [
            {
                "email": "client@ooredoo.com",
                "password": "client123",
                "role": "client",
            },
            {
                "email": "admin@ooredoo.com",
                "password": "admin123",
                "role": "admin",
            },
            {
                "email": "superadmin@ooredoo.com",
                "password": "superadmin123",
                "role": "super_admin",
            }
        ]
        
        for account in test_accounts:
            existing = db.query(Utilisateur).filter(
                Utilisateur.email == account["email"]
            ).first()
            
            if not existing:
                user = Utilisateur(
                    email=account["email"],
                    mot_de_passe_hash=hash_password(account["password"]),
                    role=account["role"]
                )
                db.add(user)
                print(f"   ✓ Created user: {account['email']} ({account['role']})")
            else:
                print(f"   - User exists: {account['email']}")
        
        db.commit()
        print("✅ Test users created successfully")
        
    except Exception as e:
        print(f"❌ Failed to create test users: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_sample_models():
    """Create sample AI models for testing."""
    print("✅ Creating sample AI models...")
    
    db = SessionLocal()
    try:
        sample_models = [
            {
                "nom": "llama3.1:8b",
                "fournisseur": "Meta",
                "version": "3.1-8B",
                "cout_par_1k_tokens": 0.0001
            },
            {
                "nom": "mistral:7b",
                "fournisseur": "Mistral AI",
                "version": "7B",
                "cout_par_1k_tokens": 0.0002
            },
            {
                "nom": "gpt-3.5-turbo",
                "fournisseur": "OpenAI",
                "version": "3.5 Turbo",
                "cout_par_1k_tokens": 0.002
            },
            {
                "nom": "claude-3-haiku",
                "fournisseur": "Anthropic",
                "version": "Haiku",
                "cout_par_1k_tokens": 0.0015
            }
        ]
        
        for model_data in sample_models:
            existing = db.query(Modele).filter(
                Modele.nom == model_data["nom"]
            ).first()
            
            if not existing:
                model = Modele(**model_data)
                db.add(model)
                print(f"   ✓ Created model: {model_data['nom']}")
            else:
                print(f"   - Model exists: {model_data['nom']}")
        
        db.commit()
        print("✅ Sample models created successfully")
        
    except Exception as e:
        print(f"❌ Failed to create sample models: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_sample_scenarios():
    """Create sample benchmark scenarios."""
    print("✅ Creating sample benchmark scenarios...")
    
    db = SessionLocal()
    try:
        sample_scenarios = [
            {
                "departement": "RH",
                "metier": "Recrutement",
                "nom_cas_usage": "Rédaction d'offre d'emploi",
                "prompt": "Rédigez une offre d'emploi attractive pour un poste de développeur senior.",
                "sortie_attendue": "Une offre d'emploi structurée avec description du poste, compétences requises, et avantages",
                "critere_succes": "Clarté, structure, attractivité pour les candidats"
            },
            {
                "departement": "Marketing",
                "metier": "Communication",
                "nom_cas_usage": "Création de contenu publicitaire",
                "prompt": "Créez un slogan accrocheur pour une nouvelle offre mobile 5G.",
                "sortie_attendue": "Un slogan court, mémorable et impactant",
                "critere_succes": "Impact, mémorabilité, alignement avec la marque"
            },
            {
                "departement": "IT",
                "metier": "Développement",
                "nom_cas_usage": "Documentation technique",
                "prompt": "Documentez une API REST pour la gestion des clients.",
                "sortie_attendue": "Documentation claire avec exemples d'utilisation",
                "critere_succes": "Clarté technique, complétude, exemples pratiques"
            },
            {
                "departement": "Service Client",
                "metier": "Support",
                "nom_cas_usage": "Réponse automatisée FAQ",
                "prompt": "Répondez à la question : Comment résilier mon abonnement ?",
                "sortie_attendue": "Procédure claire étape par étape",
                "critere_succes": "Clarté, complétude, ton approprié"
            }
        ]
        
        for scenario_data in sample_scenarios:
            existing = db.query(Scenario).filter(
                Scenario.nom_cas_usage == scenario_data["nom_cas_usage"],
                Scenario.departement == scenario_data["departement"]
            ).first()
            
            if not existing:
                scenario = Scenario(**scenario_data)
                db.add(scenario)
                print(f"   ✓ Created scenario: {scenario_data['departement']} - {scenario_data['nom_cas_usage']}")
            else:
                print(f"   - Scenario exists: {scenario_data['departement']} - {scenario_data['nom_cas_usage']}")
        
        db.commit()
        print("✅ Sample scenarios created successfully")
        
    except Exception as e:
        print(f"❌ Failed to create sample scenarios: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()