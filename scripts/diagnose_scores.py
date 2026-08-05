"""Diagnostic helper: listes de contrôles pour scores/executions.

Usage:
  .venv\Scripts\python.exe scripts/diagnose_scores.py
"""
from sqlalchemy import text
import pandas as pd
import sys

sys.path.insert(0, r'c:\Users\ranim\OneDrive\Bureau\ooredoo-ia-benchmark')
from src.database.connection import engine

queries = {
    'models_counts': "SELECT m.nom as modele, count(e.id) as nb_exec FROM executions e JOIN modeles m ON m.id=e.modele_id GROUP BY m.nom ORDER BY m.nom",
    'models_scores': "SELECT m.nom as modele, count(DISTINCT e.id) FILTER (WHERE s.id IS NOT NULL) as nb_exec_with_scores, count(DISTINCT e.id) as nb_exec_total FROM executions e LEFT JOIN scores s ON s.execution_id=e.id JOIN modeles m ON m.id=e.modele_id GROUP BY m.nom ORDER BY m.nom",
    'distinct_score_global_notes': "SELECT DISTINCT note FROM scores WHERE critere='score_global' ORDER BY note DESC",
    'score_global_gt1': "SELECT execution_id, note, critere FROM scores WHERE critere='score_global' AND note > 1 ORDER BY note DESC LIMIT 100",
    'executions_no_scores': "SELECT e.id, m.nom as modele, e.date_execution FROM executions e JOIN modeles m ON m.id=e.modele_id WHERE NOT EXISTS (SELECT 1 FROM scores s WHERE s.execution_id=e.id) ORDER BY e.date_execution DESC",
    'gemma_qwen_execs': "SELECT e.id, m.nom as modele, e.date_execution FROM executions e JOIN modeles m ON m.id=e.modele_id WHERE m.nom ILIKE '%gemma%' OR m.nom ILIKE '%qwen%' ORDER BY e.date_execution DESC",
    'nb_scores_per_execution': "SELECT e.id as execution_id, m.nom as modele, count(s.id) as nb_scores, e.date_execution FROM executions e JOIN modeles m ON m.id=e.modele_id LEFT JOIN scores s ON s.execution_id=e.id GROUP BY e.id, m.nom ORDER BY nb_scores ASC, e.date_execution DESC LIMIT 200"
}


def run():
    with engine.connect() as conn:
        for key, q in queries.items():
            print('\n---', key, '---')
            try:
                df = pd.read_sql(text(q), conn)
                if df.empty:
                    print('<no rows>')
                else:
                    print(df.to_string(index=False))
            except Exception as e:
                print('ERROR running', key, e)


if __name__ == '__main__':
    run()
