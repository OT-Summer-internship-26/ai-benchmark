# Login Testing Guide

## Quick Start

1. **Start the app:**
   ```bash
   cd c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark
   streamlit run src/dashboard/app.py
   ```

2. **Browser opens to:** `http://localhost:8501`

3. **You should see:** 
   - Ooredoo logo
   - "Benchmark IA" title
   - "Accéder à la plateforme →" button

---

## Test Case 1: Valid Client Login

**Objective**: Verify client role can login successfully

**Steps**:
1. Click "Accéder à la plateforme →"
2. Select "👤 Utilisateur" (Client) role
3. Enter email: `client@ooredoo.com`
4. Enter password: `password123`
5. Click "Se connecter"

**Expected Result**:
- ✓ Green "Connexion réussie ✓" message appears briefly
- ✓ Page redirects to client dashboard
- ✓ Title shows "Benchmark IA"
- ✓ Sidebar shows "👤 Utilisateur" role indicator
- ✓ No error messages

**If it fails**:
- ❌ Red error message should appear
- ❌ Example: "Identifiants invalides." (if email/password wrong)
- ❌ Form stays open (not blank)
- ❌ User can retry immediately

---

## Test Case 2: Valid Admin Login

**Objective**: Verify admin role can login and sees admin features

**Steps**:
1. On the login page (or back button)
2. Go back to role selection
3. Select "🛠️ Administrateur" (Admin) role
4. Enter email: `admin@ooredoo.com`
5. Enter password: `password123`
6. Click "Se connecter"

**Expected Result**:
- ✓ Green "Connexion réussie ✓" message appears briefly
- ✓ Page redirects to admin dashboard
- ✓ Sidebar shows "🛠️ Administrateur" role indicator
- ✓ Admin sees: "Filtres", "Affichage & style", "Export avancé", "Pilotage" tab
- ✓ Extra "Pilotage" tab visible (for benchmark control)

**If it fails**:
- ❌ Red error should appear immediately
- ❌ Form stays open

---

## Test Case 3: Valid Super Admin Login

**Objective**: Verify super admin role can login and sees admin + user management

**Steps**:
1. Go back to role selection
2. Select "🔐 Super Admin" role
3. Enter email: `superadmin@ooredoo.com`
4. Enter password: `password123`
5. Click "Se connecter"

**Expected Result**:
- ✓ Green "Connexion réussie ✓" message appears briefly
- ✓ Page redirects to admin dashboard
- ✓ Sidebar shows "🔐 Super Admin" role indicator
- ✓ Extra "Administration" tab visible (for user management)
- ✓ "Administration" tab shows:
  - Metrics (Exécutions chargées, Modèles, Scénarios, etc.)
  - User management section
  - "Gestion des utilisateurs" with tables

**If it fails**:
- ❌ Red error should appear immediately
- ❌ Form stays open

---

## Test Case 4: Invalid Email (Role Mismatch)

**Objective**: Verify error when using wrong role

**Steps**:
1. Go to role selection
2. Select "🛠️ Administrateur" (Admin)
3. Enter email: `client@ooredoo.com` (WRONG ROLE)
4. Enter password: `password123`
5. Click "Se connecter"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Ce compte est enregistré comme « Utilisateur », pas « Administrateur »..."
- ✓ Form stays open
- ✓ User can click back and select correct role

**This tests**: Role mismatch detection and immediate error display

---

## Test Case 5: Invalid Password

**Objective**: Verify error handling for wrong password

**Steps**:
1. At any login form
2. Enter correct email: `client@ooredoo.com`
3. Enter WRONG password: `wrongpassword`
4. Click "Se connecter"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Identifiants invalides."
- ✓ Form stays open
- ✓ User can retry with correct password

**This tests**: Immediate error feedback, form doesn't disappear

---

## Test Case 6: Non-existent Email

**Objective**: Verify error handling for unknown email

**Steps**:
1. At any login form
2. Enter non-existent email: `unknown@example.com`
3. Enter password: `password123`
4. Click "Se connecter"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Identifiants invalides."
- ✓ Form stays open
- ✓ User can retry

---

## Test Case 7: Empty Email/Password

**Objective**: Verify validation for empty fields

**Steps**:
1. At login form
2. Leave email EMPTY
3. Leave password EMPTY
4. Click "Se connecter"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Veuillez remplir tous les champs."
- ✓ Form stays open

---

## Test Case 8: Create New Client Account

**Objective**: Verify signup works and auto-logs in

**Steps**:
1. Go to role selection
2. Select "👤 Utilisateur" (Client)
3. Select "Créer un compte" tab
4. Enter NEW email: `newuser@example.com` (must not exist)
5. Enter password: `newpassword123`
6. Confirm password: `newpassword123`
7. Click "Créer un compte"

**Expected Result**:
- ✓ Green "Compte créé ✓ Connexion en cours..." message
- ✓ Page redirects to client dashboard
- ✓ New user is automatically logged in (no need to click login again)
- ✓ Sidebar shows "👤 Utilisateur"

**This tests**: Signup flow, auto-login after signup, immediate success feedback

---

## Test Case 9: Signup with Existing Email

**Objective**: Verify duplicate account prevention

**Steps**:
1. Go to signup form
2. Enter existing email: `client@ooredoo.com`
3. Enter password: `password123`
4. Confirm password: `password123`
5. Click "Créer un compte"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Un compte existe déjà avec cette adresse e-mail."
- ✓ Form stays open
- ✓ User can go back and use login instead

---

## Test Case 10: Signup with Mismatched Passwords

**Objective**: Verify password confirmation validation

**Steps**:
1. Go to signup form
2. Enter email: `testuser@example.com`
3. Enter password: `password123`
4. Confirm password: `differentpassword` (MISMATCH)
5. Click "Créer un compte"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Les mots de passe ne correspondent pas."
- ✓ Form stays open

---

## Test Case 11: Signup with Weak Password

**Objective**: Verify minimum password length requirement

**Steps**:
1. Go to signup form
2. Enter email: `testuser@example.com`
3. Enter password: `short` (LESS THAN 6 CHARS)
4. Confirm password: `short`
5. Click "Créer un compte"

**Expected Result**:
- ✓ Red error message appears IMMEDIATELY
- ✓ Error text: "Le mot de passe doit contenir au moins 6 caractères."
- ✓ Form stays open

---

## Success Criteria

All tests should show these behaviors:

| Behavior | Result |
|----------|--------|
| ✓ Errors appear immediately (same page) | RED st.error() message visible |
| ✓ Success appears immediately (same page) | GREEN st.success() message visible |
| ✓ Form doesn't disappear on error | User can retry without restarting |
| ✓ Correct dashboard after login | Client/Admin/Super Admin views correct |
| ✓ No silent failures | Every error has a visible message |
| ✓ Password masking | Password input shows dots, not text |
| ✓ Responsive design | Mobile/tablet login still works |

---

## Troubleshooting

### "Button does nothing"
- **Check**: Did you see any message (error or success)?
- **If no**: Something is wrong with error display (regression)
- **If red error**: Expected behavior, that's correct!

### "Page disappeared"
- **Check**: Is it redirecting to dashboard? (Loading)
- **If yes**: Normal, wait a moment
- **If no**: Check browser console for errors (F12 → Console tab)

### "Can't see password field"
- **Check**: Try clicking in the password field
- **If shows**: Might be CSS issue, try different browser

### "Database error"
- **Message**: "Erreur base de données: ..."
- **Check**: Is database running? (if using external DB)
- **Try**: Restart app, check `.env` database credentials

### "I created an account but can't log in with it"
- **Check**: Did you see "Compte créé ✓"?
- **If yes**: You should be auto-logged in (check if dashboard showed up)
- **If no**: Signup failed, try again with different email

---

## What to Report if Tests Fail

If any test fails, please provide:
1. **Test case number** (which test failed?)
2. **What you did** (step by step)
3. **What you expected to see** (success/error)
4. **What actually happened** (screenshot or description)
5. **Browser console errors** (F12 → Console tab)
6. **Terminal output** (what was printed when you clicked the button?)

---

## After Testing

Once all tests pass:
1. ✓ Login flow is production-ready
2. ✓ Error handling is robust
3. ✓ User experience is clear
4. ✓ Silent failures are eliminated
5. ✓ Role-based access control works

**Next**: Phase 5 would involve integrating with actual authorization/access control per role.
