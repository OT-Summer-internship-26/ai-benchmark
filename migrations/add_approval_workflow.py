"""
Migration: Add approval workflow fields to utilisateurs table.

Adds:
- is_approved BOOLEAN DEFAULT FALSE
- nom_complet TEXT

Run:
  python migrations/add_approval_workflow.py --dry-run  # Preview changes
  python migrations/add_approval_workflow.py --apply    # Apply migration
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import engine
from sqlalchemy import text


MIGRATION_SQL = """
-- Add approval workflow columns
ALTER TABLE utilisateurs 
ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;

ALTER TABLE utilisateurs 
ADD COLUMN IF NOT EXISTS nom_complet TEXT;

-- Set existing accounts to approved
UPDATE utilisateurs 
SET is_approved = TRUE 
WHERE is_approved IS NULL OR is_approved = FALSE;

-- Add index for pending approvals query
CREATE INDEX IF NOT EXISTS idx_utilisateurs_approval 
ON utilisateurs(is_approved) WHERE is_approved = FALSE;
"""

ROLLBACK_SQL = """
-- Rollback: Remove approval workflow columns
ALTER TABLE utilisateurs DROP COLUMN IF EXISTS is_approved;
ALTER TABLE utilisateurs DROP COLUMN IF EXISTS nom_complet;
DROP INDEX IF EXISTS idx_utilisateurs_approval;
"""


def dry_run():
    """Show what the migration would do."""
    print("=" * 80)
    print("DRY RUN - Migration Preview")
    print("=" * 80)
    print("\nSQL to be executed:\n")
    print(MIGRATION_SQL)
    print("\n" + "=" * 80)
    print("Checking current table structure...")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Check current columns
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'utilisateurs'
            ORDER BY ordinal_position
        """))
        
        print("\nCurrent utilisateurs columns:")
        for row in result:
            print(f"  - {row.column_name:20s} {row.data_type:15s} "
                  f"{'NULL' if row.is_nullable == 'YES' else 'NOT NULL':10s} "
                  f"default={row.column_default or 'none'}")
        
        # Check if columns already exist
        existing_cols = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'utilisateurs' 
            AND column_name IN ('is_approved', 'nom_complet')
        """)).fetchall()
        
        print(f"\nColumns to add: is_approved, nom_complet")
        if existing_cols:
            print(f"⚠️  Some columns already exist: {[c[0] for c in existing_cols]}")
            print("   Migration is idempotent - safe to run.")
        else:
            print("✓ Columns don't exist - migration will add them.")
        
        # Check existing users
        user_count = conn.execute(text("SELECT COUNT(*) FROM utilisateurs")).scalar()
        print(f"\nExisting users: {user_count}")
        print(f"These will be set to is_approved=TRUE after migration.")
    
    print("\n" + "=" * 80)
    print("To apply: python migrations/add_approval_workflow.py --apply")
    print("=" * 80)


def apply_migration():
    """Apply the migration."""
    print("=" * 80)
    print("APPLYING MIGRATION")
    print("=" * 80)
    
    with engine.begin() as conn:
        print("\nExecuting SQL...")
        conn.execute(text(MIGRATION_SQL))
        print("✓ Migration applied successfully")
    
    # Verify in separate transaction
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_approved = TRUE) as approved,
                COUNT(*) FILTER (WHERE is_approved = FALSE) as pending
            FROM utilisateurs
        """)).fetchone()
        
        print(f"\nVerification:")
        print(f"  Total users: {result.total}")
        print(f"  Approved: {result.approved}")
        print(f"  Pending: {result.pending}")
    
    print("\n" + "=" * 80)
    print("✓ Migration complete!")
    print("=" * 80)


def rollback_migration():
    """Rollback the migration (for testing)."""
    print("=" * 80)
    print("ROLLING BACK MIGRATION")
    print("=" * 80)
    
    confirm = input("Are you sure you want to rollback? This will delete data. (yes/no): ")
    if confirm.lower() != 'yes':
        print("Rollback cancelled.")
        return
    
    with engine.begin() as conn:
        print("\nExecuting rollback SQL...")
        conn.execute(text(ROLLBACK_SQL))
        conn.commit()
        print("✓ Rollback complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add approval workflow to utilisateurs table")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without applying")
    parser.add_argument("--apply", action="store_true", help="Apply migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration (destructive)")
    
    args = parser.parse_args()
    
    if args.dry_run:
        dry_run()
    elif args.apply:
        apply_migration()
    elif args.rollback:
        rollback_migration()
    else:
        print("Usage:")
        print("  python migrations/add_approval_workflow.py --dry-run")
        print("  python migrations/add_approval_workflow.py --apply")
        print("  python migrations/add_approval_workflow.py --rollback")
