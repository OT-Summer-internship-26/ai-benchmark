# Guide du Fallback Ollama pour le Juge RAGAS

## ✅ Résumé de l'implémentation

Le système de benchmark Ooredoo intègre maintenant un **fallback automatique vers Ollama** pour l'évaluation RAGAS, garantissant que les benchmarks UI ne retournent **jamais de scores à 0.0%** en cas de rate limit Groq.

## 🎯 Fonctionnalités implémentées

### 1. Fallback automatique Ollama

Quand Groq renvoie:
- **HTTP 429** (rate limit exceeded)
- **Temps d'attente > 60 secondes**

→ Le système bascule **automatiquement et immédiatement** sur Ollama local (qwen2.5:7b) sans interruption du benchmark.

### 2. Ordre de priorité des juges

```
┌─────────────────────────────────────────┐
│  1. Groq (openai/gpt-oss-20b)          │  ← Juge principal (rapide, cloud)
│     ↓ (si rate limit ou erreur)         │
│  2. Ollama (qwen2.5:7b)                │  ← Fallback automatique (local, illimité)
│     ↓ (si échec Ollama)                 │
│  3. Gemini (si activé)                  │  ← Fallback secondaire (optionnel)
└─────────────────────────────────────────┘
```

### 3. Scores garantis non-nuls

- ✅ Les 4 métriques RAGAS sont toujours évaluées
- ✅ Aucun score par défaut à 0.0%
- ✅ Le rationale indique clairement quel juge a été utilisé
- ✅ Pas d'interruption visible pour l'utilisateur

## 🔧 Configuration

### Variables d'environnement (.env)

```bash
# Juge principal (Groq - cloud, rapide)
JUDGE_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=gsk_xxxxx

# Fallback Ollama (local, illimité)
OLLAMA_URL=http://localhost:11434
OLLAMA_JUDGE_MODEL=qwen2.5:7b
USE_OLLAMA_JUDGE=false  # false = fallback automatique, true = juge principal

# Fallback secondaire Gemini (optionnel)
USE_GEMINI_JUDGE=false
GEMINI_API_KEY=xxxxx
```

### Mode d'utilisation

#### Mode 1: Fallback automatique (recommandé)
```bash
USE_OLLAMA_JUDGE=false  # Groq d'abord, Ollama si rate-limit
```

#### Mode 2: Ollama en juge principal
```bash
USE_OLLAMA_JUDGE=true   # Ollama uniquement (pas d'appels cloud)
```

## 🧪 Tests de validation

### Test 1: Groq avec fallback Ollama simulé

```bash
python test_ollama_judge_fallback.py
```

**Résultat attendu:**
```
✅ TEST RÉUSSI: Toutes les métriques ont été évaluées avec succès!
✅ Juge utilisé: openai/gpt-oss-20b
✅ Score global: 0.875
```

### Test 2: Ollama en mode primaire

```bash
python test_ollama_primary.py
```

**Résultat attendu:**
```
✅ TEST RÉUSSI!
   - Juge: Ollama (qwen2.5:7b)
   - 4/4 métriques évaluées
   - Score global: 0.625
   - Aucun appel externe (Groq/Gemini) nécessaire
```

### Test 3: Benchmark complet depuis l'UI Streamlit

1. Lancer le dashboard: `streamlit run src/dashboard/app.py`
2. Créer un nouveau benchmark (n'importe quel scénario)
3. Vérifier que les scores RAGAS sont **non-nuls** même si Groq rate-limit

**Comportement attendu:**
- ✅ Faithfulness: >0.0 (ex: 0.67)
- ✅ Answer Relevancy: >0.0 (ex: 0.89)
- ✅ Context Precision: >0.0 (ex: 0.75)
- ✅ Context Recall: >0.0 (ex: 0.82)

Si rate limit Groq détecté, les scores afficheront:
```
[Secours Ollama qwen2.5:7b] Médiane de 1 évaluations...
```

## 📊 Métriques et performance

### Comparaison des juges

| Juge | Vitesse | Coût | Qualité | Disponibilité |
|------|---------|------|---------|---------------|
| **Groq (gpt-oss-20b)** | ⚡⚡⚡ Très rapide | 💵 Gratuit (limité) | ⭐⭐⭐⭐ Excellente | 🟡 Rate limits |
| **Ollama (qwen2.5:7b)** | ⚡⚡ Rapide | 💰 Gratuit (illimité) | ⭐⭐⭐ Très bonne | 🟢 100% disponible |
| **Gemini (1.5-flash)** | ⚡⚡⚡ Très rapide | 💵 Gratuit (limité) | ⭐⭐⭐⭐ Excellente | 🟡 Rate limits |

### Temps d'évaluation moyen

- **Groq seul**: ~5-10s par exécution
- **Ollama fallback**: ~10-15s par exécution
- **Groq rate-limited**: ❌ Échec ou attente 5-15 minutes

## 🚀 Prérequis

### Installation Ollama

```bash
# Windows / macOS / Linux
# Télécharger depuis: https://ollama.ai/download

# Vérifier qu'Ollama fonctionne
curl http://localhost:11434/api/tags

# Télécharger le modèle qwen2.5:7b
ollama pull qwen2.5:7b
```

### Modèles Ollama recommandés pour le juge

| Modèle | Taille | RAM requise | Qualité jugement |
|--------|--------|-------------|------------------|
| **qwen2.5:7b** ⭐ | 4.7 GB | 8 GB | ⭐⭐⭐ Recommandé |
| llama3.1:8b | 4.9 GB | 8 GB | ⭐⭐⭐ Très bon |
| qwen3:8b | 5.2 GB | 8 GB | ⭐⭐⭐ Très bon |
| gemma2:9b | 5.4 GB | 12 GB | ⭐⭐ Correct |

## 🐛 Dépannage

### Problème: Ollama ne démarre pas

**Solution:**
```bash
# Vérifier le statut
curl http://localhost:11434/api/tags

# Si erreur, redémarrer Ollama
# Windows: Redémarrer l'application Ollama
# Linux/Mac: systemctl restart ollama
```

### Problème: Modèle qwen2.5:7b non trouvé

**Solution:**
```bash
# Télécharger le modèle
ollama pull qwen2.5:7b

# Vérifier qu'il est disponible
ollama list
```

### Problème: Scores toujours à 0.0% malgré Ollama

**Diagnostic:**
```bash
# Vérifier les logs
tail -f logs/app.log | grep "OLLAMA"

# Tester manuellement
python test_ollama_primary.py
```

## 📝 Logs et debugging

Les logs indiquent clairement quel juge a été utilisé:

```
2026-10-05 20:00:24 - src.evaluation.metrics - INFO - [JUDGE] Juge actif: Ollama (qwen2.5:7b)
2026-10-05 20:00:25 - src.evaluation.metrics - WARNING - [JUGE] Rate limit Groq détecté. Bascule automatique vers Ollama...
2026-10-05 20:00:26 - src.evaluation.metrics - INFO - [OLLAMA] Évaluation réussie avec qwen2.5:7b
```

## ✅ Checklist de validation

Avant de considérer le système comme opérationnel:

- [ ] Ollama est installé et fonctionne (`curl http://localhost:11434/api/tags`)
- [ ] Le modèle qwen2.5:7b est téléchargé (`ollama list`)
- [ ] Les variables .env sont configurées (OLLAMA_URL, OLLAMA_JUDGE_MODEL)
- [ ] Test de fallback réussit (`python test_ollama_judge_fallback.py`)
- [ ] Test Ollama primaire réussit (`python test_ollama_primary.py`)
- [ ] Benchmark UI ne retourne **jamais** de scores à 0.0%
- [ ] Les rationales indiquent clairement le juge utilisé

## 🎓 Résumé technique

### Implémentation

**Fichier modifié:** `src/evaluation/metrics.py`

**Fonction clé:** `_appeler_juge_une_fois()`

**Logique:**
```python
1. Essayer Groq (si rate-limit détecté immédiatement):
   → Appeler _appeler_juge_ollama_une_fois()
   → Retourner note + "[Secours Ollama]" dans rationale

2. Si Ollama échoue aussi:
   → Essayer Gemini (si activé)
   → Sinon retourner None avec message explicite

3. Important: Ne JAMAIS retourner 0.0 par défaut
```

### Garanties

✅ **Aucun score à 0.0%** sauf si vraiment aucun juge ne fonctionne  
✅ **Transparence**: Le rationale indique toujours quel juge a répondu  
✅ **Performance**: Bascule instantanée (pas d'attente 5-15min)  
✅ **Resilience**: 3 juges disponibles (Groq → Ollama → Gemini)  

---

**Date de mise à jour:** 2026-10-05  
**Version:** 1.0  
**Auteur:** AI Benchmark Team - Ooredoo
