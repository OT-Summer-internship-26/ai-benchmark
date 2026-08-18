#!/usr/bin/env python3
"""
Phase 2: Seed client users with departments for query-level gating tests
Maps test clients to different departments for testing isolation
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.database.connection import engine

print('='*80)
print('PHASE 2: Assign departments to client users')
print('='*80)

# Define test client-to-department mappings
client_mappings = [
    ('client@ooredoo.com', 'IT & Architecture'),
    ('ranimbarbouchi1@gmail.com', 'Marketing & Digital'),
]

with engine.connect() as conn:
    for email, dept in client_mappings:
        print(f'\nAssigning {email} → {dept}')
        
        update_query = text("""
            UPDATE utilisateurs 
            SET departement = :dept 
            WHERE email = :email AND role = 'client'
        """)
        
        try:
            result = conn.execute(update_query, {'dept': dept, 'email': email})
            conn.commit()
            
            if result.rowcount > 0:
                print(f'  ✓ Updated {result.rowcount} row(s)')
            else:
                print(f'  ⚠ No matching client user found')
        except Exception as e:
            print(f'  ❌ Error: {e}')
            conn.rollback()
    
    # Show final state
    print('\n' + '='*80)
    print('Final client user mappings:')
    print('='*80)
    
    query = text("""
        SELECT id, email, role, departement 
        FROM utilisateurs 
        WHERE role = 'client'
        ORDER BY email
    """)
    
    rows = conn.execute(query).fetchall()
    for row in rows:
        print(f'{row[1]:<40} → {row[3] or "NOT ASSIGNED"}')

print('='*80)
