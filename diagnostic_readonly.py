"""
DIAGNOSTIC EN LECTURE SEULE - AUCUNE MODIFICATION
Exécute 4 requêtes SQL pour analyser l'état des scores Ragas
"""
from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL
import pandas as pd

engine = create_engine(DATABASE_URL)

print("=" * 80)
print("DIAGNOSTIC EN LECTURE SEULE - SCORES RAGAS")
print("=" * 80)

with engine.connect() as conn:
    # Requête 1
    print("\n" + "=" * 80)
    print("REQUÊTE 1 : Nombre d'exécutions avec scores Ragas complets")
    print("=" * 80)
    query1 = text("""
        SELECT COUNT(DISTINCT execution_id) AS nb_executions_avec_ragas
        FROM scores 
        WHERE critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
    """)
    result1 = pd.read_sql(query1, conn)
    print(result1.to_string(index=False))
    
    # Requête 2
    print("\n" + "=" * 80)
    print("REQUÊTE 2 : Détail échantillon traité (290, 295, 296, 298)")
    print("=" * 80)
    query2 = text("""
        SELECT execution_id, critere, methode, is_legacy, note 
        FROM scores 
        WHERE execution_id IN (290, 295, 296, 298)
        ORDER BY execution_id, critere
    """)
    result2 = pd.read_sql(query2, conn)
    print(result2.to_string(index=False))
    
    # Requête 3
    print("\n" + "=" * 80)
    print("REQUÊTE 3 : Nombre d'exécutions orphelines (sans scores Ragas)")
    print("=" * 80)
    query3 = text("""
        SELECT COUNT(*) AS nb_executions_orphelines
        FROM executions e 
        WHERE NOT EXISTS (
          SELECT 1 FROM scores s 
          WHERE s.execution_id = e.id 
          AND s.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
        )
    """)
    result3 = pd.read_sql(query3, conn)
    print(result3.to_string(index=False))
    
    # Requête 4
    print("\n" + "=" * 80)
    print("REQUÊTE 4 : Répartition methode/is_legacy sur TOUTE la table scores")
    print("=" * 80)
    query4 = text("""
        SELECT methode, is_legacy, COUNT(*) as count
        FROM scores 
        GROUP BY methode, is_legacy
        ORDER BY methode, is_legacy
    """)
    result4 = pd.read_sql(query4, conn)
    print(result4.to_string(index=False))
    
    # Statistiques complémentaires
    print("\n" + "=" * 80)
    print("STATISTIQUES COMPLÉMENTAIRES")
    print("=" * 80)
    
    # Total exécutions
    result = conn.execute(text("SELECT COUNT(*) FROM executions"))
    total_exec = result.scalar()
    print(f"Total exécutions en base : {total_exec}")
    
    # Total scores
    result = conn.execute(text("SELECT COUNT(*) FROM scores"))
    total_scores = result.scalar()
    print(f"Total lignes dans scores : {total_scores}")
    
    # Exécutions avec au moins 1 score Ragas
    exec_avec_ragas = result1['nb_executions_avec_ragas'].iloc[0]
    print(f"Exécutions avec ≥1 score Ragas : {exec_avec_ragas}")
    
    # Exécutions orphelines
    exec_orphelines = result3['nb_executions_orphelines'].iloc[0]
    print(f"Exécutions orphelines (0 scores Ragas) : {exec_orphelines}")
    
    print("\n" + "=" * 80)
    print("FIN DU DIAGNOSTIC")
    print("=" * 80)
