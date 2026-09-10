# ⚡ Quick Start : Langfuse + Toxicity/Harmfulness

## 🎯 Ce qui a été ajouté

### 1. Langfuse Observability (Monitoring LLM)
- ✅ Traçage automatique de tous les appels LLM
- ✅ Tracking des tokens et coûts par exécution
- ✅ Nouvelle colonne `executions.tokens_utilises`
- ✅ Intégration **non-bloquante** (fonctionne sans Langfuse configuré)

### 2. Nouvelles Métriques d'Évaluation
- ✅ **Toxicity** : Détecte le langage offensant/inapproprié (0.0 = sûr, 1.0 = toxique)
- ✅ **Harmfulness** : Détecte les conseils dangereux (0.0 = sûr, 1.0 = dangereux)
- ✅ Compatible avec le pipeline existant (pas de breaking changes)

---

## 🚀 Installation (3 étapes)

### Étape 1 : Installer Langfuse
```powershell
pip install langfuse
```

### Étape 2 : Migrer la base de données
```powershell
# Vérifier ce qui sera modifié
python scripts/add_tokens_column_migration.py --dry-run

# Appliquer la migration
python scripts/add_tokens_column_migration.py --apply
```

### Étape 3 : (Optionnel) Configurer Langfuse

Si vous voulez le monitoring Langfuse, ajouter dans `.env` :
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Obtenir les clés** : https://cloud.langfuse.com (inscription gratuite)

**Si vous ne configurez pas Langfuse** : Le pipeline fonctionnera normalement sans monitoring (pas d'erreur).

---

## ✅ Tester que tout fonctionne

### Test 1 : Pipeline sans Langfuse
```powershell
# Commenter les variables Langfuse dans .env
python scripts/test_pipeline_complet.py
```

**Résultat attendu** : Log "Langfuse non configuré, monitoring désactivé" + pipeline s'exécute normalement.

### Test 2 : Vérifier les nouvelles métriques
```powershell
# Lancer une évaluation
python scripts/run_full_benchmark.py
```

**Vérifier en base** :
```sql
SELECT critere, note, commentaire 
FROM scores 
WHERE critere IN ('toxicity', 'harmfulness')
LIMIT 10;
```

### Test 3 : Vérifier le tracking des tokens
```sql
SELECT 
    e.id,
    m.nom as modele,
    e.tokens_utilises,
    e.cout_estime,
    e.latence_secondes
FROM executions e
JOIN modeles m ON m.id = e.modele_id
ORDER BY e.id DESC
LIMIT 10;
```

**Résultat attendu** : `tokens_utilises > 0` et `cout_estime > 0.0` pour les nouvelles exécutions.

---

## 📊 Ce qui a changé dans votre code

### Avant (clients LLM)
```python
response = generate_response(question, context_chunks, model_name)
```

### Après
```python
response, usage_stats = generate_response(question, context_chunks, model_name)
# usage_stats contient: prompt_tokens, completion_tokens, total_tokens, latency, estimated_cost
```

**Impact** : Automatiquement géré dans `agent_executeur.py` — **aucune modification requise** dans vos scripts existants.

---

### Avant (évaluation)
```python
resultat = evaluer_execution_ragas(...)
# Retourne: faithfulness, answer_relevancy, context_precision, context_recall, score_global
```

### Après
```python
resultat = evaluer_execution_ragas(...)
# Retourne: les 4 métriques RAGAS + toxicity + harmfulness + score_global
# score_global = moyenne des 4 RAGAS uniquement (pas de breaking change)
```

**Impact** : Les nouvelles métriques sont **ajoutées**, pas remplacées — **totalement rétrocompatible**.

---

## 🔍 Ré-évaluer des exécutions existantes

Pour ajouter les nouvelles métriques sur des exécutions passées :

```powershell
# Dry-run (voir ce qui sera fait)
python scripts/re_evaluate_executions.py --ids 1,2,3,4,5 --dry-run

# Appliquer
python scripts/re_evaluate_executions.py --ids 1,2,3,4,5 --apply
```

---

## 📚 Documentation Complète

- **Guide de Déploiement Complet** : `LANGFUSE_DEPLOYMENT_GUIDE.md`
- **Résumé Technique** : `IMPLEMENTATION_SUMMARY.md`
- **Documentation Langfuse** : https://langfuse.com/docs

---

## ❓ FAQ Rapide

### Q: Dois-je obligatoirement configurer Langfuse?
**R:** Non. Si Langfuse n'est pas configuré, le pipeline fonctionne normalement sans monitoring. Le tracking des tokens/coûts en base fonctionne indépendamment de Langfuse.

### Q: Les exécutions existantes perdent-elles leurs données?
**R:** Non. Les exécutions existantes auront `tokens_utilises = 0` (valeur par défaut). Seules les nouvelles exécutions auront des valeurs réelles. Vous pouvez ré-évaluer si besoin.

### Q: Le score_global change-t-il?
**R:** Non. Le `score_global` reste la moyenne des 4 métriques RAGAS originales. Les nouvelles métriques sont retournées séparément.

### Q: Cela coûte-t-il plus cher en appels API?
**R:** Oui, +50% d'appels Groq (6 métriques au lieu de 4). Sur un benchmark de 64 exécutions : 384 appels au lieu de 256. Le tier gratuit Groq (1K RPD) devrait suffire.

### Q: Puis-je ignorer les nouvelles métriques dans le dashboard?
**R:** Oui. Si votre dashboard Streamlit ne les affiche pas encore, elles seront simplement stockées en base et disponibles pour une future intégration.

---

## 🐛 Problème?

### Langfuse ne se connecte pas
```powershell
# Vérifier les variables d'environnement
Get-Content .env | Select-String "LANGFUSE"

# Tester sans Langfuse
# Commenter les variables LANGFUSE_* dans .env
python scripts/test_pipeline_complet.py
```

### Migration échoue
```powershell
# Vérifier que PostgreSQL tourne
psql -U ooredoo_user -d ai_benchmark -c "\dt"

# Vérifier si la colonne existe déjà
psql -U ooredoo_user -d ai_benchmark -c "SELECT column_name FROM information_schema.columns WHERE table_name='executions' AND column_name='tokens_utilises';"
```

### Nouvelles métriques ne s'affichent pas
```powershell
# Vérifier que le code est à jour
python -c "from src.evaluation.metrics import evaluer_toxicity, evaluer_harmfulness; print('OK')"

# Relancer une évaluation
python scripts/run_full_benchmark.py
```

---

**🎉 C'est tout ! Le système est prêt à l'emploi.**

Pour plus de détails, voir `LANGFUSE_DEPLOYMENT_GUIDE.md`.
