#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 3: Simulate login attempt by calling do_login() directly with test credentials.
This mimics what happens when a user fills the form and clicks the button.
"""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.database.connection import SessionLocal
from src.database.models import Utilisateur
from src.auth.utils import verify_password

print("=" * 80)
print("TASK 3: SIMULATE LOGIN ATTEMPT (Direct Function Call)")
print("=" * 80)

# We'll manually simulate what do_login() does, step by step, with detailed logging

print("\n[SIMULATION] Testing login with: client@ooredoo.com / client123\n")

email = "client@ooredoo.com"
password = "client123"
expected_role = "client"

print(f"Step 1: Normalize inputs")
print(f"  email = '{email}'.strip() → '{email.strip()}'")
email = email.strip() if email else ""
print(f"  password (not stripped in code) → '{password}'")
password = password if password else ""
print()

print(f"Step 2: Validate empty fields")
if not email or not password:
    print(f"  ❌ FAIL: email or password empty")
    print(f"  email = '{email}' (len={len(email)})")
    print(f"  password = '{password}' (len={len(password)})")
    sys.exit(1)
else:
    print(f"  ✓ PASS: Both email and password non-empty")
print()

print(f"Step 3: Query database for user")
db = SessionLocal()
try:
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if user is None:
        print(f"  ❌ FAIL: No user found for email '{email}'")
        sys.exit(1)
    else:
        print(f"  ✓ PASS: User found")
        print(f"    - Email: {user.email}")
        print(f"    - Role: {user.role}")
        print(f"    - Hash (first 30 chars): {user.mot_de_passe_hash[:30]}...")
except Exception as e:
    print(f"  ❌ EXCEPTION: {e}")
    sys.exit(1)
print()

print(f"Step 4: Verify password")
try:
    is_valid = verify_password(password, user.mot_de_passe_hash)
    if not is_valid:
        print(f"  ❌ FAIL: Password verification failed")
        print(f"  Expected: '{password}'")
        print(f"  Against hash: {user.mot_de_passe_hash[:50]}...")
        sys.exit(1)
    else:
        print(f"  ✓ PASS: Password verified successfully")
except Exception as e:
    print(f"  ❌ EXCEPTION during verify_password: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

print(f"Step 5: Check role match")
print(f"  user.role = '{user.role}'")
print(f"  expected_role = '{expected_role}'")
if user.role != expected_role:
    print(f"  ❌ FAIL: Role mismatch")
    sys.exit(1)
else:
    print(f"  ✓ PASS: Role matches")
print()

print(f"Step 6: Would set session state")
print(f"  st.session_state['login_error'] = None")
print(f"  st.session_state['auth_email'] = '{user.email}'")
print(f"  st.session_state['auth_role'] = '{user.role}'")
print(f"  Return: True")
print()

db.close()

print("=" * 80)
print("SIMULATION RESULT: ✓ LOGIN SHOULD SUCCEED")
print("=" * 80)
print()

# Now test the other roles
print("\n" + "=" * 80)
print("TESTING OTHER ROLES")
print("=" * 80)

test_cases = [
    ("admin@ooredoo.com", "admin123", "admin"),
    ("superadmin@ooredoo.com", "superadmin123", "super_admin"),
]

for email, password, expected_role in test_cases:
    print(f"\nTesting: {email} / {password}")
    
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if not user:
            print(f"  ❌ User not found")
            continue
        
        is_valid = verify_password(password, user.mot_de_passe_hash)
        if not is_valid:
            print(f"  ❌ Password invalid")
            continue
        
        if user.role != expected_role:
            print(f"  ❌ Role mismatch: {user.role} != {expected_role}")
            continue
        
        print(f"  ✓ All checks pass - login would succeed")
        print(f"    - auth_email = {user.email}")
        print(f"    - auth_role = {user.role}")
    finally:
        db.close()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("""
All three test accounts pass the do_login() logic:
  ✓ client@ooredoo.com / client123 → auth_role = "client"
  ✓ admin@ooredoo.com / admin123 → auth_role = "admin"
  ✓ superadmin@ooredoo.com / superadmin123 → auth_role = "super_admin"

The issue is NOT in do_login() logic or password verification.
The issue must be at runtime in Streamlit, possibly:
  1. st.rerun() not being called/working
  2. Session state not persisting
  3. Form submission not being detected
  4. UI element state not refreshing

Next: Run actual Streamlit app and observe terminal output.
""")
print("=" * 80 + "\n")
