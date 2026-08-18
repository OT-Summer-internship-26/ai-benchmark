#!/usr/bin/env python3
"""
Phase 2 Migration: Add departement column to utilisateurs table
This maps each client user to a specific department for query-level gating
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.database.connection import engine

print('='*80)
print('PHASE 2 MIGRATION: Add departement column to utilisateurs table')
print('='*80)

with engine.connect() as conn:
    # Check if column already exists
    check_query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='utilisateurs' AND column_name='departement'
    """)
    
    result = conn.execute(check_query).fetchone()
    
    if result:
        print('✓ Column "departement" already exists in utilisateurs table')
    else:
        print('Adding "departement" column to utilisateurs table...')
        
        alter_query = text("""
            ALTER TABLE utilisateurs ADD COLUMN departement VARCHAR NULL
        """)
        
        try:
            conn.execute(alter_query)
            conn.commit()
            print('✓ Column added successfully')
        except Exception as e:
            print(f'❌ Error: {e}')
            conn.rollback()
            sys.exit(1)
    
    # Verify the column exists and show current state
    verify_query = text("""
        SELECT id, email, role, departement 
        FROM utilisateurs 
        LIMIT 5
    """)
    
    print('\nCurrent utilisateurs (sample):')
    rows = conn.execute(verify_query).fetchall()
    for row in rows:
        print(f'  ID={row[0]}, Email={row[1]}, Role={row[2]}, Dept={row[3]}')

print('='*80)
print('Migration complete')
print('='*80)
