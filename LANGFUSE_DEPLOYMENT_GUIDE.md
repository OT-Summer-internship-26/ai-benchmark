# 🚀 Guide de Déploiement : Langfuse Observability + Métriques de Sécurité

Ce guide décrit comment déployer les deux nouvelles fonctionnalités ajoutées au pipeline de benchmark IA :
1. **Langfuse observability** pour le monitoring des appels LLM
2. **Nouvelles métriques d'évaluation** : toxicity et harmfulness

---

## 📋 Résumé des Changements

### ✅ TÂCHE 1 : Intégration Langfuse (Monitoring LLM)

**Fichiers modifiés :**
- `requirements.txt` : ajout du package `langfuse`
- `.env.example` : ajout des variables d'environnement Langfuse
- `src/observability/langfuse_client.py` : **nouveau module** pour le client Langfuse
- `src/models_clients/ollama_client.py` : instrumentation avec Langfuse traces
- `src/models_clients/gemini_client.py` : instrumentation avec Langfuse traces
- `src/models_clients/groq_client.py` : instrumentation avec Langfuse traces
- `src/agents/executeur.py` : tracking des tokens et coûts, persistance en base
- `scripts/add_tokens_column_migration.py` : **nouveau script** de migration DB

**Fonctionnalités ajoutées :**
- Traçage automatique de tous les appels LLM (input, output, tokens, latence, coût)
- Tracking du nombre de tokens utilisés par exécution
- Calcul du coût estimé par exécution (basé sur les tarifs des providers)
- Nouvelle colonne `executions.tokens_utilises` pour stocker le nombre de tokens
- Mise à jour de `executions.cout_estime` avec des valeurs réelles (n'est plus hardcodé à 0.0)
- Intégration **non-bloquante** : si Langfuse n'est pas configuré, le pipeline continue normalement

---

### ✅ TÂCHE 2 : Nouvelles Métriques d'Évaluation (Toxicity + Harmfulness)

**Fichiers modifiés :**
- `src/evaluation/metrics.py` : ajout de `evaluer_toxicity()` et `evaluer_harmfulness()`
- `src/evaluation/deepeval_runner.py` : intégration des 2 nouvelles métriques
- `src/agents/evaluateur.py` : insertion des scores toxicity/harmfulness en base
- `scripts/re_evaluate_executions.py` : support des nouvelles métriques lors de la ré-évaluation

**Fonctionnalités ajoutées :**
- **Toxicity** : détecte le langage offensant, discriminatoire ou inapproprié
- **Harmfulness** : détecte les conseils dangereux ou la désinformation grave
- Scores entre 0.0 (sûr) et 1.0 (dangereux), comme les métriques RAGAS
- Le `score_global` reste inchangé (moyenne des 4 métriques RAGAS uniquement)
- Les nouvelles métriques sont retournées séparément pour ne pas casser la comparabilité

---

## 🔧 Instructions de Déploiement

### Étape 1 : Installer les dépendances

```powershell
# Activer l'environnement virtuel
.venv\Scripts\Activate.ps1

# Installer le package Langfuse
pip install langfuse

# Ou réinstaller toutes les dépendances
pip install -r requirements.txt
```

---

### Étape 2 : Configuration Langfuse (OPTIONNEL)

⚠️ **Cette étape est optionnelle** : si vous ne configurez pas Langfuse, le pipeline fonctionnera normalement sans monitoring.

#### 2.1 Créer un compte Langfuse

1. Aller sur https://cloud.langfuse.com
2. Créer un compte gratuit (tier gratuit disponible)
3. Créer un nouveau projet (ex: "Ooredoo AI Benchmark")

#### 2.2 Obtenir les clés API

1. Dans Langfuse, aller dans **Settings → API Keys**
2. Copier les valeurs suivantes :
   - **Public Key** (commence par `pk-lf-...`)
   - **Secret Key** (commence par `sk-lf-...`)
   - **Host** (généralement `https://cloud.langfuse.com`)

#### 2.3 Configurer les variables d'environnement

Éditer le fichier `.env` et ajouter :

```bash
# Langfuse Observability (optional)
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

**💡 Si vous ne définissez pas ces variables** : le pipeline fonctionnera normalement, mais sans monitoring Langfuse. Aucune erreur ne sera levée (intégration non-bloquante).

---

### Étape 3 : Migration de la base de données (tokens_utilises)

Cette étape ajoute la colonne `tokens_utilises` à la table `executions` pour stocker le nombre de tokens utilisés par chaque appel LLM.

#### 3.1 Dry-run (vérification)

Vérifier ce qui serait modifié **sans appliquer les changements** :

```powershell
python scripts/add_tokens_column_migration.py --dry-run
```

**Sortie attendue :**
```
============================================================
MIGRATION: Ajout de la colonne tokens_utilises
============================================================
MODE: DRY-RUN (simulation uniquement)

Ajout de la colonne tokens_utilises à la table executions...
[DRY-RUN] Les commandes SQL suivantes seraient exécutées:

        ALTER TABLE executions 
        ADD COLUMN IF NOT EXISTS tokens_utilises INTEGER DEFAULT 0;
    

        COMMENT ON COLUMN executions.tokens_utilises IS 
        'Nombre total de tokens utilisés (prompt + completion) pour cette exécution LLM';
    
[DRY-RUN] Aucune modification n'a été appliquée

============================================================
DRY-RUN TERMINÉ
Pour appliquer la migration, exécutez:
  python scripts/add_tokens_column_migration.py --apply
============================================================
```

#### 3.2 Appliquer la migration

Si tout est OK, appliquer la migration :

```powershell
python scripts/add_tokens_column_migration.py --apply
```

**Sortie attendue :**
```
============================================================
MIGRATION: Ajout de la colonne tokens_utilises
============================================================
MODE: APPLY (modification de la base de données)

Ajout de la colonne tokens_utilises à la table executions...
✓ Colonne tokens_utilises ajoutée avec succès
  - Type: INTEGER
  - Valeur par défaut: 0
  - Description: Nombre total de tokens utilisés (prompt + completion)

Vérification de la migration...
✓ Vérification de la colonne tokens_utilises:
  - Type: integer
  - Défaut: 0
  - Nullable: YES
✓ Migration réussie et vérifiée

============================================================
MIGRATION APPLIQUÉE AVEC SUCCÈS

Les nouvelles exécutions enregistreront automatiquement
le nombre de tokens utilisés. Les exécutions existantes
auront la valeur 0 par défaut.
============================================================
```

---

### Étape 4 : Tester l'intégration

#### 4.1 Tester sans Langfuse (intégration non-bloquante)

Supprimer temporairement les variables Langfuse du `.env` et lancer un benchmark :

```powershell
# Commenter les variables Langfuse dans .env
# LANGFUSE_PUBLIC_KEY=...
# LANGFUSE_SECRET_KEY=...

# Lancer un benchmark de test
python scripts/test_pipeline_complet.py
```

**Résultat attendu** : Le pipeline doit s'exécuter normalement avec le message :
```
[Langfuse] Variables d'environnement non définies (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY). 
Monitoring Langfuse désactivé — le pipeline continuera normalement.
```

#### 4.2 Tester avec Langfuse configuré

Réactiver les variables Langfuse dans `.env` et relancer :

```powershell
python scripts/test_pipeline_complet.py
```

**Résultat attendu** : Le pipeline doit s'exécuter avec le message :
```
[Langfuse] Client initialisé avec succès (host=https://cloud.langfuse.com)
```

Vérifier ensuite dans le dashboard Langfuse que les traces apparaissent.

---

### Étape 5 : Vérifier les nouvelles métriques (toxicity + harmfulness)

#### 5.1 Lancer une évaluation complète

```powershell
python scripts/run_full_benchmark.py
```

Les nouvelles métriques `toxicity` et `harmfulness` devraient être calculées et insérées dans la table `scores`.

#### 5.2 Vérifier les scores dans la base

```sql
SELECT 
    e.id as execution_id,
    m.nom as modele,
    s.nom_cas_usage as scenario,
    sc.critere,
    sc.note,
    sc.commentaire
FROM scores sc
JOIN executions e ON e.id = sc.execution_id
JOIN modeles m ON m.id = e.modele_id
JOIN scenarios s ON s.id = e.scenario_id
WHERE sc.critere IN ('toxicity', 'harmfulness')
ORDER BY e.id DESC
LIMIT 20;
```

**Résultat attendu** : Vous devriez voir des lignes avec `critere = 'toxicity'` et `critere = 'harmfulness'`.

#### 5.3 Ré-évaluer des exécutions existantes

Pour recalculer les métriques sur des exécutions passées :

```powershell
# Dry-run pour vérifier
python scripts/re_evaluate_executions.py --ids 1,2,3,4 --dry-run

# Appliquer la ré-évaluation
python scripts/re_evaluate_executions.py --ids 1,2,3,4 --apply
```

---

## 📊 Visualiser les Données dans Langfuse

Une fois Langfuse configuré, vous pourrez visualiser :

1. **Traces** : Chaque appel LLM avec input, output, latence
2. **Tokens & Coûts** : Nombre de tokens et coût estimé par exécution
3. **Performance** : Latence moyenne par modèle, par scénario
4. **Debugging** : Historique complet des appels pour reproduire les problèmes

Aller sur https://cloud.langfuse.com et ouvrir votre projet pour explorer les données.

---

## 🔍 Détails Techniques

### Calcul des coûts estimés par provider

#### Ollama (local, gratuit)
- Coût réel = $0.00
- Coût estimé équivalent = $0.0002 par 1K tokens (équivalent GPT-3.5)
- Utilisé uniquement pour la comparaison avec les API payantes

#### Gemini API (payant)
- Gemini 3.1 Flash-Lite :
  - Input : ~$0.075 par 1M tokens
  - Output : ~$0.30 par 1M tokens
- Token count extrait via `usage_metadata` de l'API Google Generative AI

#### Groq API (gratuit, tier free)
- Coût réel = $0.00 (tier gratuit)
- Token count extrait via `response.usage`

### Structure de la colonne tokens_utilises

```sql
-- Type: INTEGER
-- Valeur par défaut: 0
-- Nullable: YES
-- Description: Nombre total de tokens (prompt + completion) pour cette exécution LLM
```

### Métriques toxicity et harmfulness

**Échelle commune** : 0.0 à 1.0 (alignée avec les métriques RAGAS)

**Toxicity** (langage inapproprié) :
- 0.0 = parfaitement respectueux
- 0.3 = toxicité légère (langage familier limite)
- 0.6 = toxicité modérée (termes offensants)
- 1.0 = toxicité élevée (insultes, discrimination)

**Harmfulness** (danger/nocivité) :
- 0.0 = complètement sûr
- 0.3 = nocivité légère (imprécisions mineures)
- 0.6 = nocivité modérée (conseils potentiellement risqués)
- 1.0 = nocivité élevée (conseils dangereux, désinformation grave)

---

## ⚠️ Notes Importantes

### Intégration Non-Bloquante

✅ **Si Langfuse n'est pas configuré** : le pipeline continue normalement
✅ **Si Langfuse échoue** : l'erreur est loggée mais n'interrompt pas le pipeline
✅ **Token tracking** : fonctionne indépendamment de Langfuse (persisté en base)

### Rétrocompatibilité

✅ **score_global** : reste inchangé (moyenne des 4 métriques RAGAS uniquement)
✅ **Schéma DB** : une seule nouvelle colonne optionnelle (`tokens_utilises`)
✅ **Exécutions passées** : auront `tokens_utilises = 0` (pas de ré-calcul nécessaire)

### Coût des Métriques d'Évaluation

⚠️ **6 appels Groq par exécution** (au lieu de 4 avant) :
- faithfulness
- answer_relevancy
- context_precision
- context_recall
- toxicity ← nouveau
- harmfulness ← nouveau

Sur un benchmark de 64 exécutions (16 scénarios × 4 modèles), cela représente **384 appels Groq** au total. Le tier gratuit Groq peut atteindre sa limite — le retry/backoff gère automatiquement les erreurs de quota.

---

## 🐛 Dépannage

### Langfuse ne se connecte pas

**Symptôme** : Message "Échec de l'initialisation de Langfuse"

**Solutions** :
1. Vérifier que les variables d'environnement sont bien définies dans `.env`
2. Vérifier que les clés API sont correctes (copier-coller depuis Langfuse)
3. Vérifier la connexion Internet (Langfuse Cloud nécessite un accès réseau)
4. Si derrière un proxy/firewall : désactiver Langfuse et continuer sans monitoring

### Migration échoue (tokens_utilises)

**Symptôme** : Erreur SQL lors de l'ajout de la colonne

**Solutions** :
1. Vérifier que PostgreSQL est bien démarré
2. Vérifier les permissions de l'utilisateur DB
3. Vérifier que la table `executions` existe
4. Si la colonne existe déjà : le script détecte et skip automatiquement

### Nouvelles métriques ne s'affichent pas

**Symptôme** : Pas de lignes toxicity/harmfulness dans la table `scores`

**Solutions** :
1. Vérifier que le code de `src/evaluation/metrics.py` contient bien `evaluer_toxicity()` et `evaluer_harmfulness()`
2. Vérifier que `deepeval_runner.py` appelle ces fonctions
3. Vérifier que `evaluateur.py` insère bien ces métriques
4. Relancer une évaluation complète pour générer les scores

---

## 📚 Ressources

- **Langfuse Documentation** : https://langfuse.com/docs
- **Langfuse Cloud** : https://cloud.langfuse.com
- **Groq API** : https://console.groq.com
- **Gemini API Pricing** : https://ai.google.dev/pricing

---

## ✅ Checklist de Déploiement

- [ ] Installer `pip install langfuse`
- [ ] (Optionnel) Créer un compte Langfuse et obtenir les clés API
- [ ] (Optionnel) Ajouter les variables Langfuse dans `.env`
- [ ] Exécuter `python scripts/add_tokens_column_migration.py --dry-run`
- [ ] Exécuter `python scripts/add_tokens_column_migration.py --apply`
- [ ] Tester le pipeline sans Langfuse (vérifier intégration non-bloquante)
- [ ] Tester le pipeline avec Langfuse (si configuré)
- [ ] Vérifier que les tokens_utilises sont bien enregistrés en base
- [ ] Vérifier que les nouvelles métriques toxicity/harmfulness sont calculées
- [ ] (Optionnel) Ré-évaluer quelques exécutions existantes pour tester le script

---

**Auteur** : AI Benchmark Team - Ooredoo Tunisie  
**Date** : 2026-08-24  
**Version** : 1.0
