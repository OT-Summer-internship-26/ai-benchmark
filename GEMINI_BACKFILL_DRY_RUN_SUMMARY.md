# Gemini 3.1 Flash-Lite Backfill Dry-Run Summary

**Date**: August 26, 2026  
**Status**: ✅ READY FOR BACKFILL (Awaiting Your Confirmation)

## 1. Exact Execution IDs to Backfill

```
[74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89]
```

**Total**: 16 executions (all from 2026-08-20, confirmed unevaluated)

## 2. Dry-Run Verification Results

### ✅ All 16 Executions Ready for Backfill

| ID  | Model                  | Scenario                             | Department              | Response | Expected Output | Current Scores |
|-----|------------------------|--------------------------------------|------------------------|----------|-----------------|-----------------|
| 74  | Gemini 3.1 Flash-Lite  | Rédaction de fiche de poste          | RH & Communication     | 569c     | PRESENT         | 0               |
| 75  | Gemini 3.1 Flash-Lite  | Tri et présélection des CV           | RH & Communication     | 408c     | PRESENT         | 0               |
| 76  | Gemini 3.1 Flash-Lite  | Préparation grille d'évaluation      | RH & Communication     | 1825c    | PRESENT         | 0               |
| 77  | Gemini 3.1 Flash-Lite  | Rédaction de communiqué interne      | RH & Communication     | 448c     | PRESENT         | 0               |
| 78  | Gemini 3.1 Flash-Lite  | Chatbot support RH (RAG)             | RH & Communication     | 182c     | PRESENT         | 0               |
| 79  | Gemini 3.1 Flash-Lite  | Génération de copies publicitaires   | Marketing & Digital    | 807c     | PRESENT         | 0               |
| 80  | Gemini 3.1 Flash-Lite  | Rédaction d'article de blog / FAQ    | Marketing & Digital    | 376c     | PRESENT         | 0               |
| 81  | Gemini 3.1 Flash-Lite  | Génération de code                   | IT & Architecture      | 465c     | PRESENT         | 0               |
| 82  | Gemini 3.1 Flash-Lite  | Modernisation de code legacy         | IT & Architecture      | 568c     | PRESENT         | 0               |
| 83  | Gemini 3.1 Flash-Lite  | Génération de documentation technique | IT & Architecture     | 298c     | PRESENT         | 0               |
| 84  | Gemini 3.1 Flash-Lite  | Résolution d'incidents complexes     | Réseau / Support Tech  | 593c     | PRESENT         | 0               |
| 85  | Gemini 3.1 Flash-Lite  | Rédaction de compte-rendu de réunion | Productivité Personnelle | 750c    | PRESENT         | 0               |
| 86  | Gemini 3.1 Flash-Lite  | Veille concurrentielle et synthèse   | Productivité Personnelle | 224c    | PRESENT         | 0               |
| 87  | Gemini 3.1 Flash-Lite  | Gestion de boîte mail saturée        | Productivité Personnelle | 341c    | PRESENT         | 0               |
| 88  | Gemini 3.1 Flash-Lite  | Chatbot service client (RAG)         | Service Client         | 159c     | PRESENT         | 0               |
| 89  | Gemini 3.1 Flash-Lite  | Analyse de sentiment sur appel client | Service Client        | 265c     | PRESENT         | 0               |

### Verification Results

✅ **All checks passed**:
- ✅ All 16 executions have valid responses (150+ characters)
- ✅ All 16 executions have sortie_attendue (expected output) populated
- ✅ All 16 executions currently have 0 scores
- ✅ No conflicts or duplicates

## 3. Expected Backfill Results

### Metrics to Insert per Execution

For each execution, the backfill will attempt to insert:

1. **faithfulness** (0.0-1.0)
   - Measures: How faithful is the response to the provided context?
   
2. **answer_relevancy** (0.0-1.0)
   - Measures: How relevant is the response to the question?
   
3. **context_precision** (0.0-1.0)
   - Measures: Are retrieved context chunks actually useful?
   
4. **context_recall** (0.0-1.0)
   - Measures: Do retrieved chunks contain all info needed for expected output?
   - **Note**: All 16 executions have sortie_attendue present, so context_recall WILL be scored
   
5. **score_global** (0.0-1.0)
   - Average of the 4 metrics above

### Expected Total Insertions

- **Score rows**: ~80 total
  - 16 executions × ~5 metrics each
  - Assuming all 4 RAGAS metrics succeed for all executions
  - Plus global score for each execution

## 4. Execution Plan

### Data Flow During Backfill

```
For each execution ID:
  1. Fetch execution data
     ├─ execution_id
     ├─ response_generee (model output)
     └─ scenario_id
     
  2. Fetch scenario data
     ├─ prompt (question)
     ├─ sortie_attendue (expected output)
     ├─ departement (for RAG filtering)
     └─ nom_cas_usage (scenario name)
  
  3. Retrieve context chunks
     └─ search_similar(prompt, departement, top_k=8)
  
  4. Evaluate with RAGAS metrics
     ├─ evaluer_faithfulness(response, chunks)
     ├─ evaluer_answer_relevancy(response, prompt)
     ├─ evaluer_context_precision(chunks, prompt)
     └─ evaluer_context_recall(chunks, expected_output)
  
  5. For each metric with note != None
     └─ INSERT INTO scores (execution_id, critere, note, commentaire)
```

### API Calls Required

⚠️ **Important**: This will make many API calls to Groq (LLM judge):
- **Total calls**: ~16 executions × 4 metrics = ~64 Groq API calls
- **Retry policy**: 3 attempts with backoff (5s, 15s, 45s)
- **Rate limiting**: May hit Groq rate limit (429 errors are handled)

### Potential Issues During Backfill

- **RAG SSL errors**: HuggingFace embeddings may have SSL certificate issues (non-blocking)
- **Groq API failures**: Rate limiting or connection errors (will retry up to 3 times)
- **Empty context chunks**: Some scenarios may have 0 RAG results (judge will still evaluate)

## 5. Command to Apply Backfill

### ⚠️ IMPORTANT: DO NOT RUN YET

After you review this plan and confirm it looks good:

```bash
python scripts/re_evaluate_executions.py --ids 74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89 --apply
```

This will:
1. ✅ Load each execution and scenario
2. ✅ Retrieve context via RAG
3. ✅ Evaluate all metrics using LLM judge
4. ✅ Insert scores to database
5. ✅ Commit transaction

**Expected duration**: 5-10 minutes (depending on API response times)

## 6. Verification After Backfill

After backfill completes, verify with:

```sql
SELECT 
    m.nom AS model,
    COUNT(DISTINCT e.id) AS executions,
    COUNT(DISTINCT sc.critere) AS unique_metrics,
    COUNT(*) AS total_scores
FROM executions e
JOIN modeles m ON m.id = e.modele_id
JOIN scores sc ON sc.execution_id = e.id
WHERE e.id IN (74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89)
GROUP BY m.nom;
```

**Expected result**: 
- 1 row (Gemini 3.1 Flash-Lite)
- 16 executions
- 5 unique metrics (faithfulness, answer_relevancy, context_precision, context_recall, score_global)
- ~80 total score rows

## 7. Rollback Plan (If Needed)

If something goes wrong, you can delete inserted scores with:

```sql
DELETE FROM scores 
WHERE execution_id IN (74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89)
  AND critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'score_global');
```

---

## ✅ Dry-Run Status

**All checks passed** ✅

- ✅ 16/16 executions are valid
- ✅ 16/16 have responses
- ✅ 16/16 have expected outputs
- ✅ 16/16 currently have 0 scores
- ✅ Ready to backfill

## 🔄 Next Step

**AWAITING YOUR CONFIRMATION**

Please review this dry-run report and confirm whether to proceed with the backfill.

Once confirmed, run:
```bash
python scripts/re_evaluate_executions.py --ids 74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89 --apply
```
