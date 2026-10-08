# RBAC & Approval Workflow - Modifications Minimales

## ✅ Modifications appliquées

### 1. Migration SQL (RÉUSSIE)

**Fichier:** `migrations/add_approval_workflow.py`

**Colonnes ajoutées:**
- `is_approved BOOLEAN DEFAULT FALSE`
- `nom_complet TEXT`

**Résultat:**
```
✓ Migration applied successfully
  Total users: 5
  Approved: 5
  Pending: 0
```

Tous les comptes existants ont été mis à `is_approved=TRUE`.

### 2. Modèle de données

**Fichier:** `src/database/models.py`

```python
class Utilisateur(Base):
    # ... champs existants ...
    is_approved = Column(Boolean, default=False, nullable=False)  # AJOUTÉ
    nom_complet = Column(String, nullable=True)  # AJOUTÉ
```

### 3. Authentification bloquante

**Fichier:** `src/auth/utils.py` - fonction `login()`

```python
# Check approval status (AJOUTÉ)
if not user.is_approved:
    msg = "Votre demande d'accès est en attente de validation par un administrateur."
    logger.warning(f"Login attempt for non-approved account: {email}")
    return None, msg
```

**Effet:** Les comptes non approuvés ne peuvent PAS se connecter.

### 4. Inscription client enrichie

**Fichier:** `src/dashboard/app.py`

**Fonction `do_signup()` modifiée:**
- Paramètres: `(email, nom_complet, departement, password, confirm_password)`
- Crée `role='client', is_approved=FALSE`
- **PAS de connexion automatique**
- Message: "Votre demande d'accès a été soumise..."

**Formulaire d'inscription:**
```python
# Champs ajoutés:
nom_complet = st.text_input("Nom complet")
departement = st.selectbox("Département", options=departments)  # Depuis scenarios
```

Département alimenté par: `SELECT DISTINCT departement FROM scenarios ORDER BY departement`

### 5. Administration - Approbations

**Fichier:** `src/dashboard/app.py`

**Fonctions ajoutées:**
```python
def admin_list_pending_approvals()  # Liste demandes en attente
def admin_approve_user(user_id, final_departement)  # Approuver
def admin_reject_user(user_id)  # Refuser (supprime le compte)
```

**Interface (onglet Administration - super_admin uniquement):**

Section "Demandes d'accès en attente" ajoutée AVANT "Gestion des utilisateurs":

```
┌─────────────────────────────────────────────────┐
│ Nom: John Doe                                   │
│ Email: john@ooredoo.tn                          │
│ Département demandé: RH                         │
│ Créé le: 24/08/2026 15:30                      │
│                                                 │
│ [Département final ▼]  [✅ Approuver] [❌ Refuser]│
└─────────────────────────────────────────────────┘
```

Département modifiable avant validation.

### 6. Suppression fichier inutilisé

**Fichier supprimé:** `src/dashboard/secure_login_page.py` (non utilisé)

### 7. Branding - Logo sans cadre

**Fichier:** `src/dashboard/app.py` - CSS

```diff
 .oi-logo-wrap img {
     position: relative;
     z-index: 1;
     width: 230px;
-    padding: 38px;
-    background: white;
-    border-radius: 40px;
-    box-shadow: 0 30px 70px rgba(0,0,0,0.38), ...;
+    padding: 0;
+    background: transparent;
+    border-radius: 0;
+    box-shadow: none;
+    filter: brightness(1.15);
 }
```

Logo affiché sans carte blanche, avec léger éclaircissement pour contraste sur fond rouge.

### 8. RBAC strict

**Fichier:** `src/dashboard/app.py` - fonction `main()`

**Rôles définis côté serveur:**
```python
role_key = st.session_state.get("auth_role_key", "client")  # De la DB
is_admin = role_key in ["admin", "super_admin"]
is_super_admin = role_key == "super_admin"
is_client = role_key == "client"
```

**Routage:**
- `client` → `render_client_recommendation_page()` puis `st.stop()`
- `admin` → Accès complet sauf Administration
- `super_admin` → Accès complet + Administration

Onglet Administration vérifié avec:
```python
if is_super_admin and admin_tab is not None:
    with admin_tab:
        # Contenu Administration
```

## 📋 Fichiers modifiés

1. ✅ `src/database/models.py` - Colonnes `is_approved`, `nom_complet`
2. ✅ `src/auth/utils.py` - Blocage login si non approuvé
3. ✅ `src/dashboard/app.py` - Inscription enrichie + approbations + branding
4. ✅ `migrations/add_approval_workflow.py` - Migration SQL (APPLIQUÉE)
5. ❌ `src/dashboard/secure_login_page.py` - SUPPRIMÉ

## 🧪 Tests de compilation

```bash
python -m py_compile src/database/models.py src/auth/utils.py src/dashboard/app.py migrations/add_approval_workflow.py
```

**Résultat:** ✅ Aucune erreur de syntaxe

## 🔐 Sécurité RBAC

### Blocage non-approuvés
- ✅ Login refuse si `is_approved=FALSE`
- ✅ Message: "Votre demande d'accès est en attente..."
- ✅ Pas de token API pour comptes non approuvés

### Isolation client
- ✅ Client redirigé immédiatement vers `render_client_recommendation_page()`
- ✅ `st.stop()` empêche accès aux onglets admin
- ✅ Département dérivé de `utilisateurs.departement` (SQL)

### Administration
- ✅ Onglet Administration vérifié côté serveur (`is_super_admin`)
- ✅ Fonctions d'approbation appellent `SessionLocal()` directement
- ✅ Super admin peut modifier département avant validation

## 🚀 Workflow complet

### Nouveau client

1. **Inscription** (login_page)
   - Remplit: email, nom complet, département, mot de passe
   - Crée: `role='client', is_approved=FALSE`
   - Message: "Votre demande d'accès a été soumise..."

2. **Tentative de connexion**
   - Bloqué par `login()` dans `utils.py`
   - Message: "Votre demande d'accès est en attente..."

3. **Super admin approuve**
   - Onglet Administration → "Demandes d'accès en attente"
   - Peut modifier département
   - Clique "✅ Approuver"
   - `is_approved=TRUE` en DB

4. **Client peut se connecter**
   - Login réussit
   - Redirigé vers `render_client_recommendation_page()`
   - Voit uniquement son département

### Admin/Super Admin

Créés directement par super admin via "Gestion des utilisateurs" avec `is_approved=TRUE` par défaut.

## ⚠️ Notes importantes

### API `/auth/login`
La modification dans `src/auth/utils.py` affecte **automatiquement** l'API car:
- L'API importe `login()` depuis `src/auth/utils`
- Même logique de blocage appliquée
- Comptes non approuvés n'obtiennent pas de token

### Client routing
La modification **minimale** réutilise `render_client_recommendation_page()` existant:
- Pas de réécriture
- Fonction déjà implémentée avec KPIs, modèle recommandé, etc.
- Appelle `get_client_department()` qui lit depuis `utilisateurs.departement`

### Branding
Logo sans cadre **fonctionne avec LOGO_B64 existant**:
- Pas besoin de `assets/ooredoo_logo.png`
- Utilise logo déjà encodé dans `src/dashboard/logo.py`
- CSS ajuste contraste avec `filter: brightness(1.15)`

## 📊 État actuel

```
Utilisateurs en base: 5
- is_approved=TRUE: 5
- is_approved=FALSE: 0
```

Tous les comptes existants peuvent se connecter normalement.

## 🔄 Prochaines étapes

1. ✅ Migration appliquée
2. ✅ Code compilé sans erreurs
3. ⏳ **LANCER L'APP POUR TESTER:**
   ```bash
   streamlit run src/dashboard/app.py
   ```

4. ⏳ Tester workflow complet:
   - Créer nouveau compte client
   - Vérifier blocage login
   - Approuver en tant que super admin
   - Vérifier connexion réussie

---

**Statut:** Code modifié et compilé  
**Migration:** Appliquée avec succès  
**Tests:** En attente de lancement app
