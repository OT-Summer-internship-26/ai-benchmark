# Notes d'Évaluation RAGAS — Benchmark IA Ooredoo

Date de mise à jour : 05 Octobre 2026  
Projet : `ooredoo-ia-benchmark`  
SGBD : PostgreSQL 16 + pgvector (`documents_vectorises`)

---

## 1. Changement de Modèle-Juge (LLM-as-a-Judge)

### Contexte et Justification
- **Ancien juge :** `qwen/qwen3.8-27b` (Groq). Ce modèle produisait une proportion excessive de zéros (jusqu'à 75% sur `context_precision` et 63% sur `context_recall`) et rencontrait des instabilités d'évaluation sur les sorties structurées JSON.
- **Modèles dépréciés/inaccessibles :** `llama-3.1-8b-instant` et `llama-3.3-70b-versatile` retournent une erreur HTTP 404 sur le compte Groq actuel et sont strictement proscrits.
- **Nouveau juge unifié :** `openai/gpt-oss-20b` hébergé sur Groq (`JUDGE_MODEL=openai/gpt-oss-20b` dans `.env`).
- **Configuration d'inférence :**
  - Modèle de raisonnement (*reasoning model*) nécessitant `max_tokens >= 1800` (jusqu'à 2000 pour la fidélité / `faithfulness`).
  - `temperature = 0`, `seed = 42`.
  - Client HTTP configuré avec `httpx.Client(verify=False)` pour traverser l'inspection MITM SSL de l'antivirus d'entreprise (Avast).
  - `JUDGE_REPETITIONS = 1`, `USE_GEMINI_JUDGE = false` : garantie que l'ensemble des exécutions est évalué par le même modèle sans bascule hétérogène.

---

## 2. Évolution de la Base de Connaissances (RAG Knowledge Base)

### Service Client
La base documentaire du département **Service Client** a été complétée et vérifiée avec 4 documents opérationnels :
1. `procedures_support_client.md` (5 819 octets) : Procédures de résiliation, portabilité entrante, gestion SIM/PUK, réclamations facturation et scripts d'accueil empathique.
2. `catalogue_offres_tarifs.md` (3 585 octets) : Grilles tarifaires prépayées (Djawaz, Flexi), forfaits postpayés (Hayyak, Poos), options roaming (Pass Passeport) et codes USSD (`*124#`, `*121#`).
3. `guide_my_ooredoo_selfcare.md` (5 181 octets) : Guide d'auto-dépannage mobile, activation de forfaits, configuration APN 4G/5G (`ooredoo.tn`).
4. `faq_clients.txt` (5 221 octets) : Questions fréquentes des abonnés.

### Ré-ingestion Vectorielle (`prep_all.py --reset`)
L'ingestion vectorielle dans la table pgvector `documents_vectorises` a été exécutée avec succès :
- **IT & Cybersécurité :** 632 chunks
- **Marketing & Digital :** 265 chunks
- **RH :** 261 chunks
- **Productivité & Transversal :** 160 chunks
- **Service Client :** 29 chunks (contre 8 chunks initialement)
- **Total :** 1 347 chunks indexés

### Diagnostic de Distance Sémantique
Le diagnostic multi-départements (`scripts.diag_all_depts`) a mis en évidence :
- Des distances L2 moyennes élevées (2.4 à 3.7) sur les scénarios IT & Cybersécurité, expliquant les scores légitimes à 0.0% pour ce département (questions très pointues sur SQL/CI-CD sans couverture documentaire directe).
- Des scores nettement positifs et différenciés sur Service Client suite à l'enrichissement (scores de 1.0 en fidélité et rappel, 0.25–0.30 en précision contextuelle).

---

## 3. Pipeline de Réévaluation Sécurisé (`reevaluate_missing_scores.py`)

Le script de réévaluation a été refactorisé avec des garanties d'intégrité strictes :
1. **Flag `--all` :** Contourne le filtre `HAVING COUNT(DISTINCT sc.critere) < 4` afin de permettre une réévaluation exhaustive de l'ensemble des 390 exécutions.
2. **Atomicité des transactions (`engine.begin()`) :**
   - Écriture conditionnée à l'obtention des 4 métriques RAGAS (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`) sous forme numérique non-None.
   - En une seule transaction : suppression des anciens enregistrements non-legacy (`DELETE FROM scores WHERE execution_id = :id AND methode = 'ragas' AND COALESCE(is_legacy, FALSE) = FALSE`) puis insertion des 4 métriques et du `score_global` (moyenne arithmétique exacte des 4).
   - Aucun état intermédiaire ou écriture partielle en cas d'interruption.
3. **Gestion des Quotas et Reprise :**
   - Sauvegarde automatique de progression (`reevaluation_progress.backup_*.json`) et suivi dans `reevaluation_progress.json`.
   - Pauses progressives (5 min puis 15 min) lors des dépassements de TPM.
   - En cas d'épuisement du quota journalier (TPD), arrêt propre avec conservation des scores antérieurs (les exécutions incomplètes conservent leurs scores existants sans écrasement).
   - Reprise transparente via l'argument `--resume`.

---

## 4. Statut des Métriques et Valeurs N/A Restantes

### État de la Base de Données au 05/10/2026
- **Doublons `(execution_id, critere)` pour les scores actifs :** 0 doublon.
- **Scores avec `methode IS NULL` :** 0 (les 112 lignes orphelines antérieures à la migration ont été étiquetées `methode = 'legacy_ragas', is_legacy = TRUE`).
- **Total exécutions couvertes dans le dashboard :** 390 / 390 exécutions (100%).

### Répartition des Métriques Actives (`methode='ragas', is_legacy=FALSE`) :
| Métrique | Évaluations Présentes | Moyenne | Min | Max | Zéros | N/A |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Faithfulness** | 390 / 390 | 0.258 | 0.000 | 1.000 | 214 | 0 |
| **Answer Relevancy** | 390 / 390 | 0.498 | 0.000 | 1.000 | 91 | 0 |
| **Context Precision** | 388 / 390 | 0.079 | 0.000 | 1.000 | 287 | 2 |
| **Context Recall** | 390 / 390 | 0.194 | 0.000 | 1.000 | 242 | 0 |
| **Score Global** | 390 / 390 | 0.257 | 0.000 | 0.812 | 21 | 0 |

### Pourquoi certaines valeurs restent N/A ou 0.0% :
1. **Les 2 `context_precision` manquants :** Exécutions 232 (RH) et 258 (IT). Elles proviennent de l'historique antérieur et seront réévaluées dès la prochaine passe `--resume`.
2. **Authenticité des 0.0% (Aucune fabrication) :**
   - Un score de 0.0% en fidélité reflète fidèlement que la réponse du modèle avance des affirmations factuelles absentes des extraits documentaires fournis.
   - Un score de 0.0% en précision ou rappel indique que la recherche documentaire n'a pas récupéré les extraits pertinents pour le cas d'usage concerné.
   - Les valeurs ne sont ni bornées arbitrairement vers le haut, ni gonflées par des valeurs par défaut.

---

## 5. Note Méthodologique Importante : Génération vs Contexte d'Évaluation

- **Décorrélation temporelle :** Les réponses des modèles (`reponse_generee` dans la table `executions`) ont été générées lors des sessions initiales de benchmark à partir des extraits RAG récupérés à cet instant précis.
- Lors de la réévaluation RAGAS, la recherche de similarité s'effectue sur la table vectorielle courante.
- Pour les départements dont la documentation n'a pas changé, le contexte est strictement identique.
- Pour le département Service Client, la base documentaire enrichie offre un meilleur contexte de rappel et de précision pour mesurer la pertinence des réponses générées.
