# Manual End-to-End Test Checklist

**For:** Ooredoo IA Benchmark Dashboard (Phase 3 Complete)
**Test Date:** _______________
**Tester Name:** _______________

---

## Pre-Test Setup

### Environment Verification
- [ ] Dashboard running: `streamlit run src/dashboard/admin_dashboard_page.py`
- [ ] Database connection active (verify no error messages on startup)
- [ ] Test data loaded (6 departments, 56 executions, 99 modern scores)
- [ ] Browser: Chrome/Firefox/Safari (latest version)
- [ ] Viewports: Desktop (1920x1080), Tablet (768x1024), Mobile (375x667)

---

## Test 1: Admin Login & Dashboard Access

### 1.1 Login as Admin
- [ ] Navigate to dashboard login page
- [ ] Username: `admin@example.com`
- [ ] Password: `admin_password_here`
- [ ] Click "Login"
- [ ] Verify: Dashboard loads without errors
- [ ] Verify: Page title shows "⚙️ Admin Dashboard"

### 1.2 Sidebar Visible & Functional
- [ ] Sidebar visible on left (not collapsed)
- [ ] Department filter dropdown present
- [ ] "Select Departments" label visible
- [ ] Multi-select enabled (checkboxes work)
- [ ] "Cascading Data" section shows Scenarios and Models metrics

### 1.3 Default View (All Departments Selected)
- [ ] First department pre-selected in filter
- [ ] Department overview metrics displayed (6 columns for 6 depts)
- [ ] Each metric shows dept name + execution count
- [ ] Tabs visible: Leaderboard, Radar Chart, Metrics Table, Raw Data

---

## Test 2: Department Filter Cascading

### 2.1 Select Single Department: RH & Communication
- [ ] Click "RH & Communication (28 exec)" in filter
- [ ] All other departments deselected
- [ ] "Cascading Data" updates:
  - [ ] Scenarios count: 5
  - [ ] Models Tested: 4 / 12
- [ ] Verify caption appears: "8 remote models pending benchmarking"

### 2.2 View Cascades to Leaderboard Tab
- [ ] Leaderboard shows only RH & Communication models
- [ ] Models listed: Llama 3.1 8B, Mistral 7B, Qwen2.5 7B, Gemma2 9B
- [ ] Ranks: #1, #2, #3, #4
- [ ] Global Score descending: 45.0% → 42.5% → 12.5% → 12.5%
- [ ] Execution counts displayed correctly

### 2.3 Select Multiple Departments: IT & Architecture + Marketing & Digital
- [ ] Deselect RH & Communication
- [ ] Select "IT & Architecture (4 exec)" + "Marketing & Digital (6 exec)"
- [ ] "Cascading Data" updates:
  - [ ] Scenarios count: 5 (3 + 2)
  - [ ] Models Tested: 4 / 12
- [ ] Leaderboard shows both departments with models ranked within each

### 2.4 Empty Selection Handling
- [ ] Deselect all departments
- [ ] Verify: Warning message appears "Please select at least one department"
- [ ] Dashboard view grayed out or disabled
- [ ] No errors in console

### 2.5 Toggle Departments
- [ ] Select: RH & Communication + Réseau / Support Technique (NOC)
- [ ] Verify: Cascading data updates
- [ ] Deselect RH & Communication (keep only NOC)
- [ ] Verify: Leaderboard refreshes to show only NOC models

---

## Test 3: Leaderboard Tab (All Active Departments)

### 3.1 Select All 4 Active Departments
- [ ] Select: RH & Communication, Réseau / Support, Marketing & Digital, IT & Architecture
- [ ] Leaderboard shows all 4 departments with model rankings

### 3.2 Verify Rankings per Department
**RH & Communication:**
- [ ] #1. Llama 3.1 8B (Ollama): 45.0% (15 exec)
- [ ] #2. Mistral 7B (Ollama): 42.5% (9 exec)
- [ ] #3. Qwen2.5 7B (Ollama): 12.5% (2 exec)
- [ ] #4. Gemma2 9B (Ollama): 12.5% (2 exec)

**Réseau / Support Technique (NOC):**
- [ ] #1. Llama 3.1 8B (Ollama): 57.5% (8 exec)
- [ ] #2. Mistral 7B (Ollama): 57.5% (8 exec)
- [ ] #3. Qwen2.5 7B (Ollama): 12.5% (1 exec)
- [ ] #4. Gemma2 9B (Ollama): 0.0% (1 exec)

**Marketing & Digital:**
- [ ] #1. Llama 3.1 8B (Ollama): 45.0% (2 exec)
- [ ] #2. Mistral 7B (Ollama): 42.9% (4 exec)

**IT & Architecture:**
- [ ] #1. Qwen2.5 7B (Ollama): 12.5% (1 exec)
- [ ] #2-4. Other models: 0.0%

### 3.3 Metric Display
- [ ] All 4 Ragas metrics shown: Faithfulness, Answer Relevancy, Context Precision, Context Recall
- [ ] Global Score calculated correctly
- [ ] Execution counts accurate
- [ ] Percentages formatted with % symbol

---

## Test 4: Radar Chart Tab

### 4.1 Single Department: RH & Communication
- [ ] Select only "RH & Communication (28 exec)"
- [ ] Click "Radar Chart" tab
- [ ] Radar chart renders without errors
- [ ] Title: "Model Comparison: RH & Communication"

### 4.2 Radar Axes Correct
- [ ] 4 axes visible:
  - [ ] Faithfulness
  - [ ] Answer Relevancy
  - [ ] Context Precision
  - [ ] Context Recall
- [ ] Each axis: 0% to 100% scale
- [ ] Grid lines visible

### 4.3 Model Traces
- [ ] 4 colored traces (one per model):
  - [ ] Llama 3.1 8B (Ollama) - blue
  - [ ] Mistral 7B (Ollama) - orange
  - [ ] Gemma2 9B (Ollama) - green
  - [ ] Qwen2.5 7B (Ollama) - red
- [ ] Traces filled with transparency
- [ ] Legend shows all 4 models
- [ ] Hover shows metric values

### 4.4 Multi-Department Error Handling
- [ ] Select 2 departments
- [ ] Click "Radar Chart" tab
- [ ] Verify: Message appears "Radar chart displays one department at a time"
- [ ] Chart not displayed
- [ ] No console errors

---

## Test 5: Metrics Table Tab

### 5.1 Single Department: RH & Communication
- [ ] Select only "RH & Communication"
- [ ] Click "Metrics Table" tab
- [ ] Table loads with 4 rows (one per model)
- [ ] Columns: Model, Faithfulness, Answer Relevancy, Context Precision, Context Recall, Global Score, Avg Latency (s), Executions

### 5.2 Data Formatting
- [ ] All percentages: `16.7%`, `66.7%`, etc.
- [ ] Latency: `43.81`, `50.69` (2 decimal places)
- [ ] NULL values: Displayed as `N/A`
- [ ] No raw floats or scientific notation

### 5.3 Multi-Department Error
- [ ] Select 2 departments
- [ ] Click "Metrics Table" tab
- [ ] Verify: Message "Metrics table displays one department at a time"
- [ ] Table not displayed

---

## Test 6: Raw Data Tab

### 6.1 Scenarios List
- [ ] Select "RH & Communication"
- [ ] Click "Raw Data" tab
- [ ] "Scenarios" section shows DataFrame
- [ ] Columns: id, nom_cas_usage, departement, execution_count
- [ ] 5 scenarios visible (RH & Communication has 5)

### 6.2 Models List
- [ ] "Models" section shows DataFrame
- [ ] Columns: id, name, execution_count
- [ ] 4 models visible (active Ollama models)

### 6.3 Complete Leaderboard
- [ ] "Complete Leaderboard" shows all rankings
- [ ] Can scroll horizontally/vertically
- [ ] All departments shown if multi-select

---

## Test 7: Client Login & Department-Specific Views

### 7.1 Login as Client - RH & Communication
- [ ] Logout as admin
- [ ] Navigate to client dashboard: `src/dashboard/client_recommendation_page.py`
- [ ] Login as: `client_rh@example.com` / `password`
- [ ] Verify: Page title "⭐ Model Recommendation for RH & Communication"

### 7.2 Client View - RH & Communication
- [ ] Verify: Can only see their department's data
- [ ] Best model displayed: "Llama 3.1 8B (Ollama)"
- [ ] Global Score: "45.0%"
- [ ] Justification text visible (generated from real metrics)
- [ ] Recommendation reasoning makes sense (not templated)

### 7.3 Test Empty Department - Conseiller Service Client
- [ ] Logout
- [ ] Login as: `client_conseil@example.com` / `password`
- [ ] Verify: Page title "⭐ Model Recommendation for Conseiller Service Client"
- [ ] Verify: Empty state message appears
- [ ] Message text: "No benchmark data available yet for Conseiller Service Client"
- [ ] Message suggests: "Contact your administrator to schedule benchmarks"
- [ ] NO error messages or raw exceptions

### 7.4 Test Empty Department - Productivité Personnelle
- [ ] Logout
- [ ] Login as: `client_prod@example.com` / `password`
- [ ] Verify: Page title "⭐ Model Recommendation for Productivité Personnelle"
- [ ] Verify: Same professional empty state as Conseiller Service Client
- [ ] Message is polished, not a "no data" error

### 7.5 Test Other Departments (Marketing, IT, Réseau)
For each department:
- [ ] Login as client for that department
- [ ] Verify: Can see best model recommendation
- [ ] Verify: Justification text generated from actual metrics
- [ ] Verify: Cannot access other departments' data (attempt to query API for another dept returns 0 rows)

**Departments to test:**
- [ ] Marketing & Digital: Best model should be visible
- [ ] IT & Architecture: Best model should be visible
- [ ] Réseau / Support Technique (NOC): Best model should be visible

---

## Test 8: Session Management & Security

### 8.1 Session Persistence
- [ ] Login as admin
- [ ] Navigate to Leaderboard tab
- [ ] Close browser tab and reopen dashboard URL
- [ ] Verify: Session still active (no re-login required)
- [ ] Verify: View remains on Leaderboard tab

### 8.2 Logout
- [ ] Click "Logout" button (if present in sidebar)
- [ ] Verify: Redirected to login page
- [ ] Verify: Session destroyed (attempting to access dashboard shows login)

### 8.3 Cross-Department Access (Security Test)
- [ ] Login as client for RH & Communication
- [ ] Attempt to query API for Marketing & Digital data (e.g., by modifying URL params)
- [ ] Verify: Returns 0 rows or access denied
- [ ] Verify: No cross-department data leakage

### 8.4 Invalid Session Token
- [ ] Login as admin
- [ ] Manually clear session cookie (browser dev tools)
- [ ] Refresh page
- [ ] Verify: Redirected to login (or appropriate error message)

---

## Test 9: Filter Cascading Edge Cases

### 9.1 No Executions Departments
- [ ] Select: "Conseiller Service Client" (0 exec) + "Productivité Personnelle" (0 exec)
- [ ] Verify: Cascading data shows:
  - [ ] Scenarios: 5 (2 + 3)
  - [ ] Models Tested: 0 / 12
- [ ] Leaderboard tab: Empty state or message
- [ ] Radar tab: No chart

### 9.2 Mixed Active + Empty Departments
- [ ] Select: "RH & Communication" (active) + "Conseiller Service Client" (empty)
- [ ] Verify: Leaderboard shows only RH & Communication models
- [ ] Verify: Empty dept doesn't cause errors

### 9.3 Single Active Department
- [ ] Select only: "Réseau / Support Technique (NOC)"
- [ ] Verify: Cascading data accurate
- [ ] Verify: Radar chart renders with 4 models
- [ ] Verify: Leaderboard shows correct rankings

---

## Test 10: Error Handling & Edge Cases

### 10.1 Chart Rendering with Limited Data
- [ ] Select: "IT & Architecture" (4 exec, 4 models)
- [ ] Open Radar Chart tab
- [ ] Verify: Chart renders without errors despite low execution count

### 10.2 Model with Partial Scores
- [ ] Select: "Gemma2 9B (Ollama)" in leaderboard
- [ ] Verify: Displays correctly even if some metrics are NULL
- [ ] Verify: Shows "N/A" for missing metrics, not errors

### 10.3 Very Long Model Names
- [ ] Verify: Model names in leaderboard not truncated incorrectly
- [ ] All text visible or properly scrollable

### 10.4 Large Execution Counts
- [ ] Verify: Execution counts (e.g., 28, 18) display correctly
- [ ] No number formatting issues

---

## Test 11: Responsive Design

### 11.1 Desktop (1920x1080)
- [ ] Sidebar visible (not collapsed)
- [ ] Filter dropdowns fully visible
- [ ] Leaderboard table readable without horizontal scroll
- [ ] Radar chart takes up appropriate space (not cramped)
- [ ] All tabs clickable and content visible

### 11.2 Tablet (768x1024)
- [ ] Sidebar collapses or slides (hamburger menu)
- [ ] Filter dropdowns still functional
- [ ] Leaderboard table may require horizontal scroll (acceptable)
- [ ] Radar chart scales down appropriately
- [ ] Tabs still clickable

### 11.3 Mobile (375x667)
- [ ] Layout adapts to single column
- [ ] Sidebar togglable (hamburger menu working)
- [ ] Filter functional (dropdowns may be smaller)
- [ ] Tables scrollable (not broken)
- [ ] Radar chart readable on mobile (may need rotation to landscape)
- [ ] No overlapping text or buttons

### 11.4 Zoom Levels
- [ ] Browser zoom 80%: All content visible, no horizontal scrolling needed
- [ ] Browser zoom 120%: Content slightly cramped but still functional, scrolling acceptable
- [ ] Browser zoom 150%: Scrolling required, but all elements accessible

---

## Test 12: Accessibility

### 12.1 Keyboard Navigation
- [ ] Tab through all elements (sidebar, filters, buttons, tabs)
- [ ] All interactive elements reachable via Tab key
- [ ] Department filter multi-select operable via keyboard
- [ ] Tab order logical (left-to-right, top-to-bottom)

### 12.2 Screen Reader (if available)
- [ ] Page title announced: "Admin Dashboard - Ooredoo IA Benchmark"
- [ ] Sections announced (Department Overview, Leaderboard, etc.)
- [ ] Metrics announced with labels (e.g., "Scenarios: 5")
- [ ] Table headers announced
- [ ] Tab names announced

### 12.3 Color Contrast
- [ ] All text readable (not too light/dark)
- [ ] Radar chart colors distinguishable
- [ ] Error messages visible (red text on white background, etc.)

### 12.4 Form Labels
- [ ] "Select Departments" label visible
- [ ] All form inputs have associated labels or aria-labels
- [ ] Dropdowns labeled

---

## Test 13: Performance & Load Times

### 13.1 Dashboard Load Time
- [ ] Open admin dashboard
- [ ] Measure time to full render: __________ seconds (target: < 3s)
- [ ] No blank/white screen longer than 1 second

### 13.2 Tab Switching
- [ ] Click between tabs (Leaderboard → Radar → Metrics → Raw Data)
- [ ] Each tab loads within 1 second
- [ ] No lag or freezing

### 13.3 Filter Changes
- [ ] Change department selection
- [ ] Cascading data updates within 1 second
- [ ] Leaderboard refreshes promptly

### 13.4 Radar Chart Render
- [ ] Select single department and open Radar tab
- [ ] Chart fully renders within 2 seconds

---

## Test 14: Data Accuracy

### 14.1 Leaderboard Scores Match Calculations
- [ ] Pick one model (e.g., Llama 3.1 8B in RH & Communication)
- [ ] Expected global score: 45.0%
- [ ] Verify all 4 metrics sum to this average:
  - [ ] Faithfulness: 16.7%
  - [ ] Answer Relevancy: 66.7%
  - [ ] Context Precision: 16.7%
  - [ ] Context Recall: 80.0%
  - [ ] Average: (16.7 + 66.7 + 16.7 + 80.0) / 4 = 45.0% ✓

### 14.2 Execution Counts
- [ ] Llama 3.1 8B (RH & Communication): 15 executions (verify in DB or Raw Data tab)
- [ ] Mistral 7B (RH & Communication): 9 executions
- [ ] Verify counts match Leaderboard display

### 14.3 Department Totals
- [ ] RH & Communication total executions: 28 (verify sum of all models)
- [ ] Réseau / Support total: 18
- [ ] Marketing & Digital total: 6
- [ ] IT & Architecture total: 4

---

## Test 15: Final Integration Check

### 15.1 End-to-End Flow
- [ ] Login (admin) ✓
- [ ] Select departments ✓
- [ ] View Leaderboard ✓
- [ ] View Radar ✓
- [ ] View Metrics ✓
- [ ] Logout ✓
- [ ] Login (client) ✓
- [ ] View client recommendation ✓
- [ ] Verify cross-dept access blocked ✓

### 15.2 No Console Errors
- [ ] Open browser console (F12)
- [ ] Perform all tests above
- [ ] Verify: No red error messages
- [ ] Verify: No warnings about missing props or unhandled errors

### 15.3 All Known Limitations Documented
- [ ] 8 remote models pending: ✓ (documented in dashboard)
- [ ] 2 empty departments: ✓ (polished empty state)
- [ ] Radar single-dept-only: ✓ (message shown)

---

## Test Results Summary

| Test Area | Pass | Fail | Notes |
|-----------|------|------|-------|
| Admin Login | [ ] | [ ] | _______________ |
| Sidebar & Filter | [ ] | [ ] | _______________ |
| Cascading Filters | [ ] | [ ] | _______________ |
| Leaderboard Tab | [ ] | [ ] | _______________ |
| Radar Chart Tab | [ ] | [ ] | _______________ |
| Metrics Table Tab | [ ] | [ ] | _______________ |
| Raw Data Tab | [ ] | [ ] | _______________ |
| Client Login (6 depts) | [ ] | [ ] | _______________ |
| Session Management | [ ] | [ ] | _______________ |
| Edge Cases | [ ] | [ ] | _______________ |
| Responsive Design | [ ] | [ ] | _______________ |
| Accessibility | [ ] | [ ] | _______________ |
| Performance | [ ] | [ ] | _______________ |
| Data Accuracy | [ ] | [ ] | _______________ |
| Integration | [ ] | [ ] | _______________ |

**Overall Result:** [ ] PASS [ ] FAIL

**Blocker Issues Found:** _________________________________________________________

**Minor Issues / Nice-to-Have Fixes:** ____________________________________________

**Tester Sign-off:** ____________________________  **Date:** ________________
