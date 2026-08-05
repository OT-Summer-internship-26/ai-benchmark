from dotenv import load_dotenv
load_dotenv()
import os
from src.config.settings import DATABASE_URL
print('DATABASE_URL set:', bool(DATABASE_URL))
print('OPENAI_API_KEY set:', bool(os.getenv('OPENAI_API_KEY')))
print('GEMINI_API_KEY set:', bool(os.getenv('GEMINI_API_KEY')))
print('ANTHROPIC_API_KEY set:', bool(os.getenv('ANTHROPIC_API_KEY')))
print('GROQ_API_KEY set:', bool(os.getenv('GROQ_API_KEY')))
from sqlalchemy import create_engine, text
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    print('public_tables:', conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar())
    try:
        print('scenario_count:', conn.execute(text('SELECT count(*) FROM scenarios')).scalar())
    except Exception as e:
        print('scenario_error:', type(e).__name__, str(e))
    try:
        print('model_count:', conn.execute(text('SELECT count(*) FROM modeles')).scalar())
    except Exception as e:
        print('model_error:', type(e).__name__, str(e))
    try:
        print('doc_chunks:', conn.execute(text('SELECT count(*) FROM documents_vectorises')).scalar())
    except Exception as e:
        print('doc_error:', type(e).__name__, str(e))
