"""
Re-evaluate executions that are missing Ragas scores.

This script identifies executions without evaluation scores and runs
the Ragas evaluation pipeline to fill the scores table.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL
from src.evaluation.deepeval_runner import evaluer_execution_ragas
from src.evaluation.metrics import MODELE_JUGE
from src.rag.vector_store import search_similar
from src.database.connection import SessionLocal
from src.database.models import Execution, Scenario, Score
from src.utils.logger import setup_logger
import pandas as pd

logger = setup_logger(__name__)

def get_executions_without_scores():
    """Find executions that don't have Ragas scores."""
    engine = create_engine(DATABASE_URL)
    
    query = text("""
        SELECT 
            e.id as execution_id,
            e.scenario_id,
            e.reponse_generee,
            s.prompt,
            s.sortie_attendue,
            s.departement,
            m.nom as model_name
        FROM executions e
        JOIN scenarios s ON e.scenario_id = s.id
        JOIN modeles m ON e.modele_id = m.id
        LEFT JOIN scores sc ON sc.execution_id = e.id 
            AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
        WHERE sc.id IS NULL
        ORDER BY e.date_execution DESC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    return df


def get_rag_chunks_for_scenario(scenario_id: int, prompt: str, departement: str):
    """Retrieve RAG chunks for a scenario."""
    try:
        # Use vector store search_similar function
        chunks = search_similar(
            query=prompt,
            departement=departement,
            top_k=8
        )
        
        if not chunks:
            logger.warning(f"No RAG chunks found for scenario {scenario_id}")
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error retrieving RAG chunks for scenario {scenario_id}: {e}")
        return []


def save_ragas_scores(execution_id: int, scores_dict: dict):
    """Save Ragas evaluation scores to database using direct SQL."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Save each metric as a separate row (EAV format)
            metrics_to_save = {
                'faithfulness': scores_dict.get('faithfulness'),
                'answer_relevancy': scores_dict.get('answer_relevancy'),
                'context_precision': scores_dict.get('context_precision'),
                'context_recall': scores_dict.get('context_recall'),
            }
            
            for critere, note in metrics_to_save.items():
                if note is not None:  # Only save non-None values
                    conn.execute(text("""
                        INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                        VALUES (:exec_id, :critere, :note, :comment, 'ragas', FALSE)
                    """), {
                        "exec_id": execution_id,
                        "critere": critere,
                        "note": note,
                        "comment": "Ragas evaluation via re-evaluation script"
                    })
            
            # Calculate and save global score
            valid_scores = [v for v in metrics_to_save.values() if v is not None]
            if valid_scores:
                global_score = sum(valid_scores) / len(valid_scores)
                conn.execute(text("""
                    INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                    VALUES (:exec_id, 'score_global', :note, :comment, 'ragas', FALSE)
                """), {
                    "exec_id": execution_id,
                    "note": global_score,
                    "comment": f"Average of {len(valid_scores)} Ragas metrics"
                })
            
            conn.commit()
            logger.info(f"[OK] Saved {len(metrics_to_save)} scores for execution {execution_id}")
            return True
        
    except Exception as e:
        logger.error(f"[ERR] Failed to save scores for execution {execution_id}: {e}")
        return False


def main():
    """Main re-evaluation logic."""
    print("=" * 80)
    print("RAGAS RE-EVALUATION FOR MISSING SCORES")
    print("=" * 80)
    
    # Step 1: Find executions without scores
    print("\n1. Finding executions without Ragas scores...")
    df_missing = get_executions_without_scores()
    
    total_missing = len(df_missing)
    print(f"   Found {total_missing} executions without scores")
    
    if total_missing == 0:
        print(f"\n✅ All executions already have scores!")
        return
    
    # Show sample
    print(f"\n   First 10 missing execution IDs: {df_missing['execution_id'].head(10).tolist()}")
    
    # Step 2: Process each execution
    print(f"\n2. Re-evaluating {total_missing} executions...")
    print(f"   Judge model: {MODELE_JUGE}")
    
    success_count = 0
    error_count = 0
    
    for idx, row in df_missing.iterrows():
        execution_id = row['execution_id']
        scenario_id = row['scenario_id']
        reponse = row['reponse_generee']
        question = row['prompt']
        sortie_attendue = row['sortie_attendue']
        departement = row['departement']
        model_name = row['model_name']
        
        print(f"\n   [{idx+1}/{total_missing}] Exec {execution_id} | {model_name}")
        
        try:
            # Get RAG chunks
            chunks_rag = get_rag_chunks_for_scenario(scenario_id, question, departement)
            
            if not chunks_rag:
                logger.warning(f"      No RAG chunks for execution {execution_id}, scores may be 0.0")
            
            # search_similar returns a list of strings (content), not dicts
            contexts = chunks_rag  # Already a list of strings
            
            # Run Ragas evaluation
            print(f"      Evaluating with Ragas (judge: {MODELE_JUGE})...")
            resultat = evaluer_execution_ragas(
                reponse=reponse,
                question=question,
                contexte_chunks=contexts,
                sortie_attendue=sortie_attendue or ""
            )
            
            # Extract scores from result dict
            scores_dict = {
                'faithfulness': resultat['faithfulness'].get('note'),
                'answer_relevancy': resultat['answer_relevancy'].get('note'),
                'context_precision': resultat['context_precision'].get('note'),
                'context_recall': resultat['context_recall'].get('note'),
            }
            
            # Display scores
            print(f"      → Faithfulness: {scores_dict.get('faithfulness', 'N/A')}")
            print(f"      → Answer Relevancy: {scores_dict.get('answer_relevancy', 'N/A')}")
            print(f"      → Context Precision: {scores_dict.get('context_precision', 'N/A')}")
            print(f"      → Context Recall: {scores_dict.get('context_recall', 'N/A')}")
            
            # Save to database
            if save_ragas_scores(execution_id, scores_dict):
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            logger.error(f"      Error evaluating execution {execution_id}: {e}")
            continue
    
    # Summary
    print("\n" + "=" * 80)
    print("RE-EVALUATION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully evaluated: {success_count}/{total_missing}")
    print(f"❌ Errors: {error_count}/{total_missing}")
    
    if success_count > 0:
        print("\n💡 Next steps:")
        print("   1. Clear Streamlit cache")
        print("   2. Refresh dashboard at http://localhost:8502")
        print("   3. Verify scores appear in the dashboard")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
