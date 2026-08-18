#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 1: Query utilisateurs table and test verify_password() for each account.
This is a reality check - don't assume previous fixes worked.
"""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import verify_password, hash_password

print("=" * 80)
print("TASK 1: VERIFY TEST ACCOUNT CREDENTIALS")
print("=" * 80)

db = SessionLocal()

# First, let's see what accounts actually exist
print("\n[STEP 1] Query all utilisateurs in database:")
try:
    users = db.query(Utilisateur).all()
    print(f"  Found {len(users)} accounts:\n")
    
    for user in users:
        print(f"    Email: {user.email}")
        print(f"    Role: {user.role}")
        print(f"    Password hash (first 50 chars): {user.mot_de_passe_hash[:50]}...")
        print()
except Exception as e:
    print(f"  [ERROR] Failed to query: {e}")
    sys.exit(1)

# Now test verify_password() against common seed values
print("\n[STEP 2] Test verify_password() against expected seed credentials:\n")

test_cases = [
    ("client@ooredoo.com", "client123", "client"),
    ("client@ooredoo.com", "password123", "client"),
    ("admin@ooredoo.com", "admin123", "admin"),
    ("admin@ooredoo.com", "password123", "admin"),
    ("superadmin@ooredoo.com", "superadmin123", "super_admin"),
    ("superadmin@ooredoo.com", "password123", "super_admin"),
]

valid_credentials = []

for email, password, expected_role in test_cases:
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    
    if not user:
        print(f"  ❌ User {email} does NOT exist in database")
        continue
    
    if user.role != expected_role:
        print(f"  ⚠️  User {email} has role '{user.role}', expected '{expected_role}'")
    
    try:
        is_valid = verify_password(password, user.mot_de_passe_hash)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"  {status}: {email} / {password}")
        
        if is_valid:
            valid_credentials.append((email, password, user.role))
    except Exception as e:
        print(f"  ❌ Exception verifying {email}: {e}")

db.close()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if not valid_credentials:
    print("\n🚨 CRITICAL: NO VALID CREDENTIALS FOUND")
    print("   The login failure may be because test accounts have no valid passwords!")
    print("\nWe need to:")
    print("  1. Create new test accounts with known passwords")
    print("  2. OR reset existing accounts with new password hashes")
    sys.exit(1)
else:
    print(f"\n✓ Found {len(valid_credentials)} valid credential pairs:\n")
    for email, password, role in valid_credentials:
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: {role}")
        print()
    
    print("These credentials can be used to test login.")

print("=" * 80 + "\n")
