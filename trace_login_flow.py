#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 2: Trace the exact code path from login button click through do_login().
This is a STATIC CODE ANALYSIS to identify where the flow breaks.
"""

import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("TASK 2: TRACE CODE PATH - STATIC ANALYSIS")
print("=" * 80)

# Read the do_login function
with open("src/dashboard/app.py", "r", encoding="utf-8") as f:
    app_code = f.read()

# Find do_login function
login_start = app_code.find("def do_login(")
login_end = app_code.find("\ndef do_signup", login_start)
do_login_code = app_code[login_start:login_end]

print("\n[ANALYSIS] do_login() function code:")
print("-" * 80)
lines = do_login_code.split('\n')
for i, line in enumerate(lines[:50], start=1):  # First 50 lines
    print(f"{i:3d}: {line}")
print("-" * 80)

print("\n[ANALYSIS] Key observations:")
print("-" * 80)

checks = [
    ("Email stripping", 'email = email.strip() if email else ""', "✓ YES" if 'email = email.strip()' in do_login_code else "❌ NO"),
    ("Password stripping", 'password = password.strip()' if 'password else' in do_login_code else "", "? (checks below)"),
    ("Empty field validation", 'if not email or not password' in do_login_code, "✓" if 'if not email or not password' in do_login_code else "❌"),
    ("DB query for user", 'db.query(Utilisateur).filter' in do_login_code, "✓" if 'db.query(Utilisateur).filter' in do_login_code else "❌"),
    ("Password verification", 'verify_password(password, user.mot_de_passe_hash)' in do_login_code, "✓" if 'verify_password' in do_login_code else "❌"),
    ("Role check", 'user.role != expected_role' in do_login_code, "✓" if 'user.role != expected_role' in do_login_code else "❌"),
    ("Session state on success", 'st.session_state["auth_role"] = user.role' in do_login_code, "✓" if 'st.session_state["auth_role"] = user.role' in do_login_code else "❌"),
    ("Try/except block", 'try:' in do_login_code and 'except Exception as e:' in do_login_code, "✓" if ('try:' in do_login_code and 'except Exception as e:' in do_login_code) else "❌"),
    ("Error message set", 'st.session_state["login_error"]' in do_login_code, "✓" if 'st.session_state["login_error"]' in do_login_code else "❌"),
    ("DB close in finally", 'finally:' in do_login_code and 'db.close()' in do_login_code, "✓" if ('finally:' in do_login_code and 'db.close()' in do_login_code) else "❌"),
]

for check_name, check_code, status in checks:
    if status in ["✓", "❌"]:
        print(f"  {status} {check_name}")

print("\n[ANALYSIS] Code path from form submission to session state:")
print("-" * 80)

# Find the login form submission handler
form_start = app_code.find('if st.session_state["login_mode"] == "signin":')
form_section = app_code[form_start:form_start+2000]

print("\nLogin form submission handler:")
print("-" * 80)
form_lines = form_section.split('\n')[:30]
for i, line in enumerate(form_lines, start=1):
    print(f"{i:3d}: {line}")

print("\n" + "=" * 80)
print("FINDINGS")
print("=" * 80)

print("""
Code path analysis:

1. User clicks "Se connecter" button in form
   ↓
2. Form closes, submitted variable set to True
   ↓
3. if submitted: block executes
   ↓
4. try: block wraps do_login() call
   ↓
5. do_login(email, password, expected_role=role_key) called
   - email is from text_input (already entered by user)
   - password is from text_input (already entered by user)
   - expected_role = role_key (from session state, should be "client", "admin", or "super_admin")
   ↓
6. Inside do_login():
   - Strips email
   - Validates email/password not empty
   - Queries database for user by email
   - Compares password using verify_password()
   - Checks user.role == expected_role
   - If all pass: Sets session_state["auth_role"] = user.role (the DATABASE role value)
   - Returns True or False
   ↓
7. Back in form handler:
   - If do_login() returns True: st.success() + st.rerun()
   - If do_login() returns False: st.error(login_error message)
   ↓
8. st.rerun() forces page reload, main() runs again
   ↓
9. main() checks if "auth_role" in st.session_state
   - If present: renders dashboard (role checking at line 929)
   - If not present: calls login_page()

POTENTIAL ISSUES TO CHECK:
- Does expected_role value match database roles? (should be client/admin/super_admin)
- Is password being stripped correctly?
- Are there any bare except blocks?
- Does st.rerun() actually trigger?
- Are there Streamlit widget caching issues?
""")

print("=" * 80 + "\n")
