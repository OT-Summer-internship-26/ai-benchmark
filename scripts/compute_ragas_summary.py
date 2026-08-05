import sys
from pathlib import Path
from sqlalchemy import text
import pandas as pd

# Ensure workspace root is on sys.path so imports like `src.*` work when run from scripts/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.connection import engine

q = '''
SELECT m.nom AS modele, COUNT(DISTINCT s.execution_id) AS nb_exec_ragas,
       ROUND(AVG(s.note)::numeric,3) AS avg_ragas_score
FROM scores s
JOIN executions e ON e.id = s.execution_id
JOIN modeles m ON m.id = e.modele_id
WHERE s.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall','score_global')
  AND s.note IS NOT NULL
GROUP BY m.nom
ORDER BY m.nom;
'''

df = pd.read_sql(text(q), engine)
print(df.to_string(index=False))

# Also print per-model execution ids that have any RAGAS metric (for inspection)
q2 = '''
SELECT m.nom AS modele, s.execution_id, s.critere, s.note
FROM scores s
JOIN executions e ON e.id = s.execution_id
JOIN modeles m ON m.id = e.modele_id
WHERE s.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall','score_global')
  AND s.note IS NOT NULL
ORDER BY m.nom, s.execution_id, s.critere;
'''

df2 = pd.read_sql(text(q2), engine)

for modele, group in df2.groupby('modele'):
    execs = sorted(group['execution_id'].unique())
    print(f"\nModele: {modele} -> executions with RAGAS: {execs}")

# Liste des executions par modèle (toutes), et celles sans RAGAS
q_all = '''
SELECT m.nom AS modele, e.id AS execution_id
FROM executions e
JOIN modeles m ON m.id = e.modele_id
ORDER BY m.nom, e.id;
'''
df_all = pd.read_sql(text(q_all), engine)

for modele, group in df_all.groupby('modele'):
  all_execs = sorted(group['execution_id'].unique())
  have = df2[df2['modele'] == modele]['execution_id'].unique().tolist()
  missing = sorted([e for e in all_execs if e not in have])
  if missing:
    print(f"Modele: {modele} -> executions WITHOUT RAGAS: {missing}")
