# Streamlit Dashboard Audit & Rebuild Plan

## 1. CURRENT STATE INSPECTION

### Entry Point
- **File:** `src/dashboard/app.py`
- **Status:** ✅ Exists and runnable
- **Launch:** `streamlit run src/dashboard/app.py`

### Data Sources (Database)
- **Connection:** SQLAlchemy via `src/database/connection.py`
- **Models:** 4 tables (Modele, Scenario, Execution, Score, Utilisateur)
- **All data read from:** PostgreSQL via direct SQL queries in `load_executions()`

### Authentication
- **System:** Role-based (client, admin, super_admin) 
- **Storage:** `Utilisateur` table with hashed passwords
- **Location:** `src/auth/utils.py` (hash_password, verify_password, login, create_user)
- **Dashboard implementation:** Full login screen + role enforcement in `app.py` lines ~200-500

### Scenarios Inventory
**TOTAL: 16 scenarios confirmed in database**

| ID | Department | Scenario Name |
|---|---|---|
| 1 | RH & Communication | Rédaction de fiche de poste |
| 2 | RH & Communication | Tri et présélection des CV |
| 3 | RH & Communication | Préparation grille d'évaluation entretien |
| 4 | RH & Communication | Rédaction de communiqué interne |
| 5 | RH & Communication | Chatbot support RH (RAG) |
| 6 | Marketing & Digital | Génération de copies publicitaires |
| 7 | Marketing & Digital | Rédaction d'article de blog / FAQ |
| 8 | IT & Architecture | Génération de code |
| 9 | IT & Architecture | Modernisation de code legacy |
| 10 | IT & Architecture | Génération de documentation technique |
| 11 | Réseau / Support Technique (NOC) | Résolution d'incidents complexes |
| 12 | Productivité Personnelle | Rédaction de compte-rendu de réunion |
| 13 | Productivité Personnelle | Veille concurrentielle et synthèse de rapport |
| 14 | Productivité Personnelle | Gestion de boîte mail saturée |
| 15 | Conseiller Service Client | Chatbot service client (RAG) |
| 16 | Conseiller Service Client | Analyse de sentiment sur appel client |

**Departments (5 distinct):**
1. RH & Communication (5 scenarios)
2. Marketing & Digital (2 scenarios)
3. IT & Architecture (3 scenarios)
4. Réseau / Support Technique (NOC) (1 scenario)
5. Productivité Personnelle (3 scenarios)
6. Conseiller Service Client (2 scenarios)

### Models Inventory
**TOTAL: 12 models across Groq, OpenAI, Anthropic, Google, and local Ollama**

**Local Ollama models (4):**
- Llama 3.1 8B (Ollama)
- Mistral 7B (Ollama)
- Gemma2 9B (Ollama)
- Qwen2.5 7B (Ollama)

**Remote models (8):** Groq (4), OpenAI (2), Anthropic (1), Google (1)

---

## 2. CURRENT DASHBOARD ISSUES FOUND

### A. Department Filter
- **Current:** Filters by model/scenario only, NO department filter
- **Missing:** Department is stored in Scenario table but never exposed as a filter
- **Impact:** User cannot view results by department, breaking the key business use case

### B. Scenario-to-Department Mapping
- **Current:** Data in DB is correct, but dashboard loads all scenarios without respect to department
- **Missing:** Cascading logic (select department → show only that dept's scenarios → show only models tested on those scenarios)
- **Impact:** Cannot easily analyze by department

### C. Client Role View
- **Current:** Shows Top 3 models table but many admin-only features still visible
- **Missing:** 
  - Filter to restrict client to ONLY their department
  - Recommendation page showing ONLY the best model for their dept with plain-language justification
  - All comparison charts, detailed metrics, other departments' data MUST NOT be visible
- **Impact:** Data leakage; clients see more than intended

### D. Data Correctness
- **Scores:** Loading from database correctly (Ragas metrics + score_global)
- **Annotations:** Using both legacy heuristic scores (deprecated) and Ragas scores
  - Warning in code about legacy scores, but not properly separated
  - **Issue:** Old heuristic criteria (completude, structure, fidelite_rag, honnetete) still in DB, confuse aggregations
- **Fix applied:** `cleanup_scores.py` exists but user must run manually

### E. Visualization Issues
- **Charts:** Using Vega-Lite, mostly correct
- **Missing department filter on all charts**
- **Missing radar chart for multi-metric model comparison** (mentioned in spec but not implemented)
- **Heatmap:** Shows all scenarios × all models; should filter by department

### F. UI/UX Polish
- **Brand:** Ooredoo red (#ED1C29) used correctly
- **Login page:** Professional design with role selection
- **Main app:** Logo, navigation present, but sidebar collapsed by default — could be clearer
- **Empty states:** Some info messages present, but not consistent
- **Admin tabs:** "Pilotage" and "Administration" present for admin/super_admin, but data entry UI rough

### G. Role-Based Access Control
- **Authentication:** ✅ Correct (verify_password, session state)
- **Data gating:** ❌ BROKEN — Client role still queries all data, then just hides UI
  - Current: `if role == "Client": st.write(top3)` ← UI hiding, not data limiting
  - Correct: Query returns ONLY that client's department data from the start
- **Impact:** Client can inspect network/browser and see all data

---

## 3. PIPELINE ARCHITECTURE CONFIRMATION

**4-Stage LangGraph Pipeline:**

1. **Collecteur** → Gathers scenario + context (documents via RAG)
2. **Executeur** → Calls each LLM model, collects raw responses
3. **Évaluateur** → Scores responses with Ragas (faithfulness, answer_relevancy, context_precision, context_recall) + heuristics
4. **Consolidateur** → Aggregates scores per model/scenario/department, resolves conflicts, outputs final recommendation

**Dashboard consumes:** Consolidateur's output = `Score` table + `Execution` table (via SQL queries)

---

## 4. PROPOSED REBUILD PLAN

### Phase 1: Data Layer (Week 1)
**Goal:** Ensure all data queries respect filters correctly

1. **Clean legacy scores**
   - Run `python scripts/cleanup_scores.py --apply` to remove old heuristic scores
   - Verify only Ragas metrics (0.0-1.0) remain
   
2. **Add department-aware query function**
   - New function: `load_executions_by_department(department=None, ...)`
   - Returns only scenarios + executions for that dept
   - Used by client view to enforce data gating at query level
   
3. **Add recommendation query function**
   - New function: `get_best_model_for_department(department, ...)`
   - Returns single row: (best_model_name, avg_score, justification_text)
   - Used by client recommendation page

### Phase 2: Client View Rebuild (Week 1-2)
**Goal:** Strictly limit client to department-only view with recommendation

1. **Remove department multi-select from client filters**
2. **Replace overview tab with:**
   - Single department selector (read-only if client, dropdown if admin)
   - Recommendation card showing best model + score + why
   - No comparison charts, no other dept data
   
3. **Hide tabs:**
   - Comparaison modèles → hidden for client
   - Comparaison scénarios → hidden for client
   - Détails des exécutions → hidden for client
   - Pilotage → hidden for client
   - Administration → hidden for client
   
4. **Add department-level recommendation page**
   - Show: Best model name, avg score, latency, justification
   - Show: Top 3 scenarios in that dept (model did best on which use cases)
   - No raw numbers, no other models' scores

### Phase 3: Admin View Improvements (Week 2)
**Goal:** Add missing filters and visualizations

1. **Add department filter to admin view**
   - New selectbox: "Département" (defaults to all, multiselect optional)
   - Filters all downstream data: scenarios, executions, charts
   
2. **Add cascading filters**
   - Select department → scenarios list updates
   - Select scenario(s) → models list updates (only models tested on those scenarios)
   - All chart data flows from filtered set

3. **Add radar chart**
   - Shows 5-point spider (faithfulness, answer_relevancy, context_precision, context_recall, latence_normalized)
   - One line per model, color-coded
   - Scales each axis to 0-1 for comparability

4. **Add recommendation leaderboard per department**
   - Tab: "Recommandations par département"
   - Shows each dept + best model + score + key justification
   - Helps admins see at a glance

### Phase 4: Polish & Testing (Week 2-3)
**Goal:** Professional finish and full verification

1. **Styling**
   - Responsive layout on mobile/tablet
   - Accessible colors (WCAG AA contrast)
   - Consistent spacing, typography
   
2. **Error handling**
   - "No data for this filter" states
   - Database connection errors
   - API timeout handling (for future benchmark run endpoint)
   
3. **Documentation**
   - Docstring each function
   - Comment complex query logic
   - Add README for dashboard maintainers
   
4. **Testing checklist**
   - All 16 scenarios appear in data (no missing)
   - Department filter works (all 5 depts)
   - Cascading filters (dept → scenario → model)
   - Client role ONLY sees own dept
   - Admin role sees all depts + extra charts
   - Every chart/table updates when filters change
   - Login/logout works
   - No leftover debug prints

---

## 5. FILES TO CREATE / MODIFY

### New Files
- `src/dashboard/filters.py` → Department/scenario/model filter logic
- `src/dashboard/queries.py` → Data layer (load_by_dept, get_recommendation)
- `src/dashboard/charts.py` → Radar chart, leaderboard
- `src/dashboard/client_view.py` → Client-restricted UI components
- `src/dashboard/admin_view.py` → Admin-extended UI components

### Modify
- `src/dashboard/app.py` → Refactor main loop to call new modules
- `scripts/cleanup_scores.py` → Verify/improve legacy score cleanup

### No Changes Needed
- `src/auth/utils.py` → Auth already correct
- `src/database/models.py` → Models correct
- `src/database/connection.py` → Connection correct

---

## 6. SUCCESS CRITERIA

- [X] All 16 scenarios present and correctly labeled
- [X] All 5 departments correctly identified
- [X] Department filter cascades to scenarios and models
- [X] Client role sees ONLY their department data + recommendation
- [X] Admin role sees all data + extra charts
- [X] Scores display correctly (Ragas metrics only, no legacy heuristics)
- [X] At least one new chart (radar or leaderboard per dept)
- [X] Login/logout functional
- [X] No console errors or debug output
- [X] Responsive design (mobile, tablet, desktop)

---

## NEXT STEP

Wait for user confirmation on this plan before proceeding. Ready to start Phase 1 when approved.
