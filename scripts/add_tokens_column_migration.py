"""
Migration script to add tokens_utilises column to executions table.

This script adds token usage tracking to support Langfuse observability integration.
The column stores the total number of tokens used for each LLM call.

Usage:
    # Dry-run mode (check what would be done):
    python scripts/add_tokens_column_migration.py --dry-run
    
    # Apply the migration:
    python scripts/add_tokens_column_migration.py --apply

Author: AI Benchmark Team - Ooredoo Tunisie
Date: 2026-08-24
"""

import argparse
import sys
import logging
from sqlalchemy import text

sys.path.insert(0, r'c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark')
from src.database.connection import engine

# Configure logger with UTF-8 console handler for Windows compatibility
# This prevents UnicodeEncodeError on Windows (cp1252) with French accents and ✓/✗ symbols
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Use the same UTF-8-safe pattern as src/utils/logger.py
try:
    # Open stdout with explicit UTF-8 encoding (works on Windows cp1252 console)
    utf8_stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1, closefd=False)
    console_handler = logging.StreamHandler(utf8_stdout)
except (OSError, AttributeError):
    # Fallback if fileno() not available (some IDEs)
    console_handler = logging.StreamHandler(sys.stdout)

console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def check_column_exists(conn) -> bool:
    """Vérifie si la colonne tokens_utilises existe déjà."""
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'executions' 
        AND column_name = 'tokens_utilises'
    """))
    return result.fetchone() is not None


def add_tokens_column(conn, dry_run: bool = True):
    """
    Ajoute la colonne tokens_utilises à la table executions.
    
    Args:
        conn: Connexion à la base de données
        dry_run: Si True, affiche les actions sans les exécuter
    """
    # Vérifier si la colonne existe déjà
    if check_column_exists(conn):
        logger.info("✓ La colonne tokens_utilises existe déjà dans la table executions")
        return
    
    logger.info("Ajout de la colonne tokens_utilises à la table executions...")
    
    migration_sql = """
        ALTER TABLE executions 
        ADD COLUMN IF NOT EXISTS tokens_utilises INTEGER DEFAULT 0;
    """
    
    migration_comment = """
        COMMENT ON COLUMN executions.tokens_utilises IS 
        'Nombre total de tokens utilisés (prompt + completion) pour cette exécution LLM';
    """
    
    if dry_run:
        logger.info("[DRY-RUN] Les commandes SQL suivantes seraient exécutées:")
        logger.info(migration_sql)
        logger.info(migration_comment)
        logger.info("[DRY-RUN] Aucune modification n'a été appliquée")
    else:
        try:
            # Exécuter la migration
            conn.execute(text(migration_sql))
            conn.execute(text(migration_comment))
            conn.commit()
            
            logger.info("✓ Colonne tokens_utilises ajoutée avec succès")
            logger.info("  - Type: INTEGER")
            logger.info("  - Valeur par défaut: 0")
            logger.info("  - Description: Nombre total de tokens utilisés (prompt + completion)")
            
        except Exception as e:
            logger.error(f"✗ Erreur lors de la migration: {str(e)}")
            conn.rollback()
            raise


def verify_migration(conn):
    """Vérifie que la migration a été appliquée correctement."""
    if not check_column_exists(conn):
        logger.error("✗ La colonne tokens_utilises n'a pas été créée")
        return False
    
    # Vérifier le type de la colonne
    result = conn.execute(text("""
        SELECT data_type, column_default, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'executions' 
        AND column_name = 'tokens_utilises'
    """))
    
    row = result.fetchone()
    if row:
        data_type, column_default, is_nullable = row
        logger.info(f"✓ Vérification de la colonne tokens_utilises:")
        logger.info(f"  - Type: {data_type}")
        logger.info(f"  - Défaut: {column_default}")
        logger.info(f"  - Nullable: {is_nullable}")
        return True
    
    return False


def main(dry_run: bool = True):
    """
    Point d'entrée principal du script de migration.
    
    Args:
        dry_run: Si True, simule la migration sans l'appliquer
    """
    logger.info("=" * 60)
    logger.info("MIGRATION: Ajout de la colonne tokens_utilises")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("MODE: DRY-RUN (simulation uniquement)")
    else:
        logger.info("MODE: APPLY (modification de la base de données)")
    
    logger.info("")
    
    try:
        with engine.connect() as conn:
            # Ajouter la colonne
            add_tokens_column(conn, dry_run=dry_run)
            
            # Vérifier la migration si elle a été appliquée
            if not dry_run:
                logger.info("")
                logger.info("Vérification de la migration...")
                if verify_migration(conn):
                    logger.info("✓ Migration réussie et vérifiée")
                else:
                    logger.error("✗ La vérification de la migration a échoué")
                    sys.exit(1)
        
        logger.info("")
        logger.info("=" * 60)
        if dry_run:
            logger.info("DRY-RUN TERMINÉ")
            logger.info("Pour appliquer la migration, exécutez:")
            logger.info("  python scripts/add_tokens_column_migration.py --apply")
        else:
            logger.info("MIGRATION APPLIQUÉE AVEC SUCCÈS")
            logger.info("")
            logger.info("Les nouvelles exécutions enregistreront automatiquement")
            logger.info("le nombre de tokens utilisés. Les exécutions existantes")
            logger.info("auront la valeur 0 par défaut.")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Erreur fatale: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Migration pour ajouter le tracking de tokens aux exécutions"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Appliquer la migration (défaut: dry-run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (défaut)"
    )
    
    args = parser.parse_args()
    
    # Si aucun flag n'est spécifié, on utilise dry-run par défaut
    if not args.apply and not args.dry_run:
        args.dry_run = True
    
    main(dry_run=not args.apply)
