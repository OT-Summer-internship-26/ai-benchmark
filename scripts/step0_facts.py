"""
scripts/step0_facts.py
Read-only script for Step 0 facts gathering:
- Lists Groq models (distinguishing 404, 429, 503, etc.)
- Inspects .env and metrics.py judge resolution
- Computes note distribution per metric per model (exact 0.0, 0.5, 1.0, None, others)
"""
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

print("=" * 80)
print("STEP 0 - FACT GATHERING")
print("=" * 80)

# (a) Groq model IDs
print("\n--- (a) Groq Available Models ---")
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("GROQ_API_KEY is missing or empty in .env!")
else:
    try:
        from groq import Groq, APIStatusError, RateLimitError, NotFoundError, InternalServerError
        client = Groq(api_key=groq_api_key, http_client=httpx.Client(verify=False))
        models_resp = client.models.list()
        print(f"Successfully retrieved {len(models_resp.data)} models:")
        for m in sorted(models_resp.data, key=lambda x: x.id):
            print(f"  - {m.id:<45} (owned_by={m.owned_by}, active={getattr(m, 'active', True)})")
    except NotFoundError as e:
        print(f"[404 NotFoundError]: {e}")
    except RateLimitError as e:
        print(f"[429 RateLimitError]: {e}")
    except InternalServerError as e:
        print(f"[503/500 InternalServerError]: {e}")
    except APIStatusError as e:
        print(f"[{e.status_code} APIStatusError]: {e}")
    except Exception as e:
        print(f"[Unexpected Error ({type(e).__name__})]: {e}")

# (b) Judge Environment and Metrics Config
print("\n--- (b) Judge Environment Variable vs metrics.py resolution ---")
print(f"os.environ.get('JUDGE_MODEL'): {os.getenv('JUDGE_MODEL')}")
print(f"os.environ.get('GROQ_JUDGE_MODEL'): {os.getenv('GROQ_JUDGE_MODEL')}")
print(f"os.environ.get('USE_GEMINI_JUDGE'): {os.getenv('USE_GEMINI_JUDGE')}")
print(f"os.environ.get('GEMINI_JUDGE_MODEL'): {os.getenv('GEMINI_JUDGE_MODEL')}")
print(f"os.environ.get('JUDGE_REPETITIONS'): {os.getenv('JUDGE_REPETITIONS')}")

from src.evaluation import metrics
print(f"metrics.MODELE_JUGE: {metrics.MODELE_JUGE}")
print(f"metrics.get_active_judge_name(): {metrics.get_active_judge_name()}")
print(f"metrics.USE_GEMINI_JUDGE: {metrics.USE_GEMINI_JUDGE}")
print(f"metrics.REPETITIONS_JUGE: {metrics.REPETITIONS_JUGE}")

# (c) Distribution of note values per metric per model
print("\n--- (c) Distribution of note values per metric per model in DB ---")
from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL
import pandas as pd

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    # Distribution of score notes
    query = text("""
        SELECT 
            m.nom AS model_name,
            s.departement,
            sc.critere,
            COUNT(sc.id) AS total_scores,
            SUM(CASE WHEN sc.note = 0.0 THEN 1 ELSE 0 END) AS count_0_0,
            SUM(CASE WHEN sc.note = 0.5 THEN 1 ELSE 0 END) AS count_0_5,
            SUM(CASE WHEN sc.note = 1.0 THEN 1 ELSE 0 END) AS count_1_0,
            SUM(CASE WHEN sc.note IS NULL THEN 1 ELSE 0 END) AS count_null,
            SUM(CASE WHEN sc.note NOT IN (0.0, 0.5, 1.0) AND sc.note IS NOT NULL THEN 1 ELSE 0 END) AS count_intermediate,
            AVG(sc.note) AS avg_note
        FROM executions e
        JOIN scenarios s ON e.scenario_id = s.id
        JOIN modeles m ON e.modele_id = m.id
        LEFT JOIN scores sc ON sc.execution_id = e.id
            AND sc.methode = 'ragas'
            AND COALESCE(sc.is_legacy, FALSE) = FALSE
            AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
        GROUP BY m.nom, s.departement, sc.critere
        ORDER BY sc.critere, m.nom, s.departement
    """)
    df = pd.read_sql(query, conn)

print(df.to_string(index=False))

# Also global summary per metric and model
print("\n--- Overall per metric and model ---")
with engine.connect() as conn:
    q_model_metric = text("""
        SELECT 
            m.nom AS model_name,
            sc.critere,
            COUNT(sc.id) AS total,
            SUM(CASE WHEN sc.note = 0.0 THEN 1 ELSE 0 END) AS zeros,
            ROUND(100.0 * SUM(CASE WHEN sc.note = 0.0 THEN 1 ELSE 0 END) / NULLIF(COUNT(sc.id), 0), 1) AS pct_0,
            SUM(CASE WHEN sc.note = 0.5 THEN 1 ELSE 0 END) AS half,
            ROUND(100.0 * SUM(CASE WHEN sc.note = 0.5 THEN 1 ELSE 0 END) / NULLIF(COUNT(sc.id), 0), 1) AS pct_05,
            SUM(CASE WHEN sc.note = 1.0 THEN 1 ELSE 0 END) AS ones,
            ROUND(100.0 * SUM(CASE WHEN sc.note = 1.0 THEN 1 ELSE 0 END) / NULLIF(COUNT(sc.id), 0), 1) AS pct_1,
            SUM(CASE WHEN sc.note NOT IN (0.0, 0.5, 1.0) AND sc.note IS NOT NULL THEN 1 ELSE 0 END) AS interm,
            ROUND(AVG(sc.note)::numeric, 3) AS avg_note
        FROM executions e
        JOIN modeles m ON e.modele_id = m.id
        LEFT JOIN scores sc ON sc.execution_id = e.id
            AND sc.methode = 'ragas'
            AND COALESCE(sc.is_legacy, FALSE) = FALSE
            AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
        WHERE sc.critere IS NOT NULL
        GROUP BY m.nom, sc.critere
        ORDER BY sc.critere, m.nom
    """)
    df_mm = pd.read_sql(q_model_metric, conn)
print(df_mm.to_string(index=False))
