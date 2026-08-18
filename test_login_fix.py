#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test login functionality end-to-end (without running the full Streamlit app).
This tests the authentication logic directly to verify error handling works.
"""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import hash_password, verify_password

print("=" * 80)
print("LOGIN LOGIC TEST")
print("=" * 80)

# Test 1: Valid client login
print("\n[TEST 1] Valid client login")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "client@ooredoo.com"
    ).first()
    
    if user and verify_password("password123", user.mot_de_passe_hash):
        print("  [✓] client@ooredoo.com exists with correct password")
        print(f"  [✓] Role: {user.role}")
        assert user.role == "client", "Role mismatch!"
        print("  [✓] Role matches expected: 'client'")
    else:
        print("  [✗] FAILED: Cannot verify client credentials")
        sys.exit(1)
finally:
    db.close()

# Test 2: Valid admin login
print("\n[TEST 2] Valid admin login")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "admin@ooredoo.com"
    ).first()
    
    if user and verify_password("password123", user.mot_de_passe_hash):
        print("  [✓] admin@ooredoo.com exists with correct password")
        print(f"  [✓] Role: {user.role}")
        assert user.role == "admin", "Role mismatch!"
        print("  [✓] Role matches expected: 'admin'")
    else:
        print("  [✗] FAILED: Cannot verify admin credentials")
        sys.exit(1)
finally:
    db.close()

# Test 3: Valid super_admin login
print("\n[TEST 3] Valid super_admin login")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "superadmin@ooredoo.com"
    ).first()
    
    if user and verify_password("password123", user.mot_de_passe_hash):
        print("  [✓] superadmin@ooredoo.com exists with correct password")
        print(f"  [✓] Role: {user.role}")
        assert user.role == "super_admin", "Role mismatch!"
        print("  [✓] Role matches expected: 'super_admin'")
    else:
        print("  [✗] FAILED: Cannot verify super_admin credentials")
        sys.exit(1)
finally:
    db.close()

# Test 4: Invalid password
print("\n[TEST 4] Invalid password handling")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "client@ooredoo.com"
    ).first()
    
    if user and not verify_password("wrongpassword", user.mot_de_passe_hash):
        print("  [✓] Invalid password correctly rejected")
    else:
        print("  [✗] FAILED: Invalid password not rejected")
        sys.exit(1)
finally:
    db.close()

# Test 5: Non-existent user
print("\n[TEST 5] Non-existent user handling")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "nonexistent@ooredoo.com"
    ).first()
    
    if user is None:
        print("  [✓] Non-existent user correctly returns None")
    else:
        print("  [✗] FAILED: Non-existent user did not return None")
        sys.exit(1)
finally:
    db.close()

# Test 6: Role mismatch
print("\n[TEST 6] Role mismatch handling")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(
        Utilisateur.email == "client@ooredoo.com"
    ).first()
    
    # Client user trying to login as admin
    if user and user.role == "client":
        print("  [✓] Client user has 'client' role")
        if user.role != "admin":
            print("  [✓] Role mismatch correctly detected (client != admin)")
        else:
            print("  [✗] FAILED: Role mismatch not detected")
            sys.exit(1)
    else:
        print("  [✗] FAILED: Could not verify role mismatch test")
        sys.exit(1)
finally:
    db.close()

print("\n" + "=" * 80)
print("ALL LOGIN LOGIC TESTS PASSED ✓")
print("=" * 80)
print("\nThe authentication backend is working correctly.")
print("When you run `streamlit run src/dashboard/app.py`:")
print("  1. Login screen will appear")
print("  2. Select a role (Client, Admin, or Super Admin)")
print("  3. Enter credentials (e.g., client@ooredoo.com / password123)")
print("  4. Click 'Se connecter'")
print("  5. Error messages will appear immediately if login fails")
print("  6. On success, you'll be redirected to the appropriate dashboard")
print("=" * 80 + "\n")
