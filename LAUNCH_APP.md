# Running the Ooredoo IA Benchmark Dashboard

## Quick Start

To launch the full application with authentication:

```bash
streamlit run src/dashboard/app.py
```

The app will be available at `http://localhost:8501`

## Available Entry Points

### 1. Full Application (Recommended for Demo Day)

**Command:**
```bash
streamlit run src/dashboard/app.py
```

**Features:**
- Complete login/signup system
- Role-based access control (Client, Admin, Super Admin)
- User management (Super Admin only)
- Benchmark execution triggering
- Full dashboard features

**Access:**
- Client users: model recommendations by department
- Admin users: department filters, leaderboards, radar charts
- Super Admin: full admin panel + user management

---

### 2. Admin Dashboard Only

**Command:**
```bash
streamlit run src/dashboard/admin_dashboard_page.py
```

**Features:**
- Department filter with cascading
- Multi-metric radar chart comparison
- Per-department leaderboard
- Metrics comparison table

**Use case:** Quick analysis without login flow

---

### 3. Client Recommendation Page Only

**Command:**
```bash
streamlit run src/dashboard/client_recommendation_page.py
```

**Features:**
- Best-recommended model for client's department
- Real Consolidateur metrics
- Query-level access gating

**Note:** Requires passing `client_email` and `client_department` as session state

---

## Path Setup (Technical Details)

All entry-point files include automatic path bootstrap at the top:

```python
import sys
import pathlib

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```

This ensures imports work regardless of which directory you run `streamlit run` from.

**Why this matters:**
- Streamlit adds the script's directory to `sys.path`, not the project root
- Without this bootstrap, `from src.xxx import ...` would fail
- The fix is applied locally to each entry point (not globally)

---

## Running from Any Directory

You can run the app from anywhere by providing the full path:

```bash
# From anywhere:
streamlit run /path/to/ooredoo-ia-benchmark/src/dashboard/app.py

# From the project root (simplest):
cd ooredoo-ia-benchmark
streamlit run src/dashboard/app.py
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"

This error means the path bootstrap isn't working. Ensure you're running from the project root:

```bash
cd c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark
streamlit run src/dashboard/app.py
```

### "Could not create log file handler"

This is a non-blocking warning. The app will still start and function normally. It occurs because log directories may not exist, but Streamlit falls back to console logging.

### Missing dependencies

If you see `ModuleNotFoundError` for plotly, requests, pydantic, or transformers:

```bash
pip install -r requirements.txt
```

---

## Demo Day Recommendation

For presentations, use:

```bash
streamlit run src/dashboard/app.py
```

This provides the full user experience with login, role-based features, and all dashboard capabilities.

**Pre-demo checklist:**
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Database initialized and populated
- [ ] Test account created (admin@ooredoo.com / password)
- [ ] Run from project root directory
- [ ] Port 8501 is available (or specify `--server.port XXXX`)

---

## Advanced: Custom Port

If port 8501 is in use, specify a different one:

```bash
streamlit run src/dashboard/app.py --server.port 8502
```

---

## Architecture Summary

**Entry Points:**
- `src/dashboard/app.py` — Main app with login
- `src/dashboard/admin_dashboard_page.py` — Admin view
- `src/dashboard/client_recommendation_page.py` — Client view

**Shared Modules:**
- `src/dashboard/admin_queries.py` — Admin-specific queries
- `src/dashboard/queries.py` — Client queries
- `src/dashboard/radar_chart.py` — Chart rendering
- `src/dashboard/filters.py` — Filter logic
- `src/dashboard/justifications.py` — Consolidateur explanations

**Supporting:**
- `src/database/` — Database models and connection
- `src/auth/` — Authentication utilities
- `requirements.txt` — All dependencies

