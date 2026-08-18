#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create test accounts for all three roles to test login flow.
"""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import hash_password

print("=" * 80)
print("CREATING TEST ACCOUNTS")
print("=" * 80)

db = SessionLocal()

test_accounts = [
    {
        "email": "client@ooredoo.com",
        "password": "password123",
        "role": "client",
        "name": "Client Test"
    },
    {
        "email": "admin@ooredoo.com",
        "password": "password123",
        "role": "admin",
        "name": "Admin Test"
    },
    {
        "email": "superadmin@ooredoo.com",
        "password": "password123",
        "role": "super_admin",
        "name": "Super Admin Test"
    }
]

try:
    for account in test_accounts:
        # Check if user exists
        existing = db.query(Utilisateur).filter(
            Utilisateur.email == account["email"]
        ).first()
        
        if existing:
            print(f"\n[SKIP] {account['email']} already exists")
            continue
        
        # Create user
        user = Utilisateur(
            email=account["email"],
            mot_de_passe_hash=hash_password(account["password"]),
            role=account["role"]
        )
        db.add(user)
        print(f"[✓] Created: {account['email']} ({account['role']})")
    
    db.commit()
    print("\n" + "=" * 80)
    print("TEST ACCOUNTS CREATED SUCCESSFULLY")
    print("=" * 80)
    print("\nYou can now test login with:")
    print("  - Email: client@ooredoo.com")
    print("    Password: password123")
    print("    Role: Client")
    print("")
    print("  - Email: admin@ooredoo.com")
    print("    Password: password123")
    print("    Role: Admin")
    print("")
    print("  - Email: superadmin@ooredoo.com")
    print("    Password: password123")
    print("    Role: Super Admin")
    print("=" * 80 + "\n")
    
except Exception as e:
    print(f"[ERROR] {e}")
    db.rollback()
finally:
    db.close()
