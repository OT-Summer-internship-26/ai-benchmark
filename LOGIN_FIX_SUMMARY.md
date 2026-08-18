# Login Button Silent Failure - Fixed

## Problems Found and Fixed

### 1. Missing `logs/` Directory (Non-blocking Warning)

**Problem**: `src/utils/logger.py` tried to write to `logs/benchmark.log` but the directory didn't exist, causing warnings on startup.

**Fix**: Modified `src/utils/logger.py` to automatically create the `logs/` directory if it doesn't exist:

```python
# Before
try:
    file_handler = RotatingFileHandler('logs/benchmark.log', ...)
except (OSError, IOError):
    logger.warning("Could not create log file handler")

# After
try:
    logs_dir = pathlib.Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)  # Create dir if missing
    
    file_handler = RotatingFileHandler('logs/benchmark.log', ...)
except (OSError, IOError) as e:
    logger.warning(f"Could not create log file handler: {e}")
```

**Result**: ✓ Warning is eliminated, logs are created successfully.

---

### 2. No Error Display on Login Failure (Critical Bug)

**Problem**: When a user clicked the login button and authentication failed, nothing happened:
- No error message appeared
- No visual feedback to the user
- The form just seemed to hang
- Errors were only checked AFTER the form block closed, so they only displayed on next page load

**Root Cause**: The login form logic was structured incorrectly:

```python
# BEFORE (WRONG)
with st.form("signin_form"):
    email = st.text_input(...)
    password = st.text_input(...)
    submitted = st.form_submit_button("Se connecter", use_container_width=True)

if submitted and do_login(email, password, expected_role=role_key):
    st.rerun()

# Error only checked AFTER form block - never shown during this page render
if st.session_state.get("login_error"):
    st.error(st.session_state["login_error"])
```

**Fix**: Restructured to show errors immediately after form submission:

```python
# AFTER (CORRECT)
with st.form("signin_form"):
    email = st.text_input(...)
    password = st.text_input(...)
    submitted = st.form_submit_button("Se connecter", use_container_width=True)

# Handle form submission IMMEDIATELY after form closes
if submitted:
    try:
        if do_login(email, password, expected_role=role_key):
            st.success("Connexion réussie ✓")
            st.session_state["login_error"] = None
            st.rerun()
        else:
            # Error already set by do_login()
            st.error(st.session_state.get("login_error", "Connexion échouée."))
    except Exception as e:
        error_msg = f"Erreur lors de la connexion : {str(e)}"
        st.session_state["login_error"] = error_msg
        st.error(error_msg)
```

**Key improvements**:
- ✓ Errors shown immediately as `st.error()` 
- ✓ Success messages shown as `st.success()`
- ✓ Try/except block catches database errors
- ✓ User gets immediate feedback on any failure

---

### 3. Weak Error Handling in `do_login()`

**Problem**: If a database error occurred, it would silently fail with no useful error message.

**Fix**: Enhanced `do_login()` with better error handling and input validation:

```python
def do_login(email: str, password: str, expected_role: str) -> bool:
    """Improved: catches all exceptions and provides clear error messages"""
    email = email.strip() if email else ""
    password = password.strip() if password else ""
    
    # Validate inputs
    if not email or not password:
        st.session_state["login_error"] = "Veuillez remplir tous les champs."
        return False
    
    db = SessionLocal()
    try:
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()

        if user is None or not verify_password(password, user.mot_de_passe_hash):
            st.session_state["login_error"] = "Identifiants invalides."
            return False

        if user.role != expected_role:
            st.session_state["login_error"] = (
                f"Ce compte est enregistré comme « {ROLE_DISPLAY.get(user.role, user.role)} », "
                f"pas « {ROLE_DISPLAY.get(expected_role, expected_role)} ». "
                "Choisissez le bon profil dans le menu."
            )
            return False

        st.session_state["login_error"] = None
        st.session_state["auth_email"] = user.email
        st.session_state["auth_role"] = ROLE_DISPLAY.get(user.role, user.role)
        return True
    except Exception as e:
        st.session_state["login_error"] = f"Erreur base de données : {str(e)}"
        return False
    finally:
        db.close()
```

---

### 4. Weak Error Handling in `do_signup()`

**Problem**: Similar to `do_login()` - signup failures weren't caught.

**Fix**: Added try/except and auto-login after successful signup:

```python
def do_signup(email: str, password: str, confirm_password: str) -> bool:
    """Improved: catches exceptions, auto-logs in after signup"""
    email = email.strip() if email else ""
    
    # ... validation ...
    
    db = SessionLocal()
    try:
        # Check if user exists, create if not
        existing = db.query(Utilisateur).filter(
            Utilisateur.email == email
        ).first()
        if existing:
            st.session_state["login_error"] = "Un compte existe déjà..."
            return False
        
        user = Utilisateur(
            email=email,
            mot_de_passe_hash=hash_password(password),
            role="client",
        )
        db.add(user)
        db.commit()
        
        # Auto-login after successful signup
        st.session_state["login_error"] = None
        st.session_state["auth_email"] = email
        st.session_state["auth_role"] = ROLE_DISPLAY.get("client", "client")
        return True
    except Exception as e:
        db.rollback()
        st.session_state["login_error"] = f"Erreur lors de la création du compte : {str(e)}"
        return False
    finally:
        db.close()
```

And in the login page, after successful signup, we auto-login:

```python
if submitted:
    try:
        if do_signup(email, password, confirm):
            st.success("Compte créé ✓ Connexion en cours...")
            if do_login(email, password, expected_role=role_key):
                st.rerun()
            else:
                st.error("Compte créé, mais connexion échouée.")
        else:
            st.error(st.session_state.get("login_error", "Création échouée."))
    except Exception as e:
        st.error(f"Erreur : {str(e)}")
```

---

## Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/utils/logger.py` | Auto-create logs directory | Eliminates "Could not create log file handler" warning |
| `src/dashboard/app.py` (lines 183-217) | Improved `do_login()` | Better error handling, input validation, clear error messages |
| `src/dashboard/app.py` (lines 226-269) | Improved `do_signup()` | Better error handling, auto-login after signup |
| `src/dashboard/app.py` (lines 808-850) | Fixed login form structure | Errors shown immediately as `st.error()`, not after page reload |

---

## Test Accounts

Three test accounts are pre-created in the database:

```
Email: client@ooredoo.com
Password: password123
Role: Client

Email: admin@ooredoo.com
Password: password123
Role: Admin

Email: superadmin@ooredoo.com
Password: password123
Role: Super Admin
```

---

## Expected Behavior After Fix

### Successful Login
1. User runs: `streamlit run src/dashboard/app.py`
2. Login screen appears
3. User selects role (Client, Admin, or Super Admin)
4. User enters valid credentials
5. User clicks "Se connecter"
6. ✓ Green "Connexion réussie ✓" message appears
7. ✓ Page redirects to appropriate dashboard (after ~1 second)

### Failed Login (Invalid Credentials)
1. User enters invalid email or password
2. User clicks "Se connecter"
3. ✓ Red error message appears IMMEDIATELY: "Identifiants invalides."
4. ✓ Form remains open, user can retry

### Failed Login (Role Mismatch)
1. User selects "Admin" role
2. User enters client@ooredoo.com credentials
3. User clicks "Se connecter"
4. ✓ Red error message appears IMMEDIATELY: "Ce compte est enregistré comme « Utilisateur », pas « Administrateur »..."
5. ✓ Form remains open, user can select correct role

### Failed Login (Database Error)
1. If database is unreachable or query fails
2. ✓ Red error message appears IMMEDIATELY: "Erreur base de données: [specific error]"
3. ✓ User knows what went wrong

### Successful Signup
1. User selects "Client" role
2. User switches to "Créer un compte"
3. User enters new email and password
4. User clicks "Créer un compte"
5. ✓ Green "Compte créé ✓ Connexion en cours..." message appears
6. ✓ User is automatically logged in
7. ✓ Page redirects to client dashboard

### Failed Signup (Account Already Exists)
1. User tries to create account with existing email
2. User clicks "Créer un compte"
3. ✓ Red error appears IMMEDIATELY: "Un compte existe déjà avec cette adresse e-mail."
4. ✓ Form remains open

### Failed Signup (Passwords Don't Match)
1. User enters mismatched passwords
2. User clicks "Créer un compte"
3. ✓ Red error appears IMMEDIATELY: "Les mots de passe ne correspondent pas."
4. ✓ Form remains open

---

## Technical Summary

### Why It Was Failing Silently Before
1. Form validation and login were in one code block
2. Error display was in a separate code block AFTER the form
3. When the form submitted, the page needed to rerun (`st.rerun()`)
4. But `st.error()` was never called before `st.rerun()`, so user never saw the error
5. The error persisted in session state and appeared on the NEXT page load
6. User perceived this as "the button did nothing"

### Why It Works Now
1. Form closes after submission
2. Error/success is checked IMMEDIATELY
3. `st.error()` or `st.success()` is called BEFORE `st.rerun()`
4. Streamlit renders the error/success message
5. Then `st.rerun()` happens (if successful)
6. User sees immediate feedback on success OR failure

---

## Verification

Run the test script to verify database connectivity:
```bash
python test_login_fix.py
```

Expected output:
```
[✓] Valid client login
[✓] Valid admin login
[✓] Valid super_admin login
[✓] Invalid password handling
[✓] Non-existent user handling
[✓] Role mismatch handling

ALL LOGIN LOGIC TESTS PASSED ✓
```

Then launch the app:
```bash
streamlit run src/dashboard/app.py
```

And test with the credentials above.
