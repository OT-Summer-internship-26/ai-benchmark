from src.database.connection import engine
from sqlalchemy import text
with engine.begin() as conn:
    conn.execute(text("UPDATE scores SET methode = 'legacy_heuristique' WHERE methode = 'heuristique' OR critere IN ('completude', 'structure', 'fidelite_rag', 'honnetete') leave_out").text.replace(' leave_out', ''))
print('Mise a jour effectuee !')
