"""
Re-evaluate executions that are missing Ragas scores.

This script identifies executions without evaluation scores and runs
the Ragas evaluation pipeline to fill the scores table.
"""

import sys
import io
import json
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 standard output and error streams for Windows compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL
from src.evaluation.metrics import (
    MODELE_JUGE,
    evaluer_faithfulness,
    evaluer_answer_relevancy,
    evaluer_context_precision,
    evaluer_context_recall,
)
from src.rag.vector_store import search_similar
from src.utils.logger import setup_logger
import pandas as pd

logger = setup_logger(__name__)

PROGRESS_FILE = "reevaluation_progress.json"


def load_progress(progress_file: str = PROGRESS_FILE) -> tuple[list[int], dict]:
    """Load existing progress from JSON file."""
    path = Path(progress_file)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                completed_ids = [int(i) for i in data.get("completed_ids", [])]
                errors = data.get("errors", {})
                return completed_ids, errors
        except Exception as e:
            logger.warning(f"Impossible de lire le fichier de progression {progress_file}: {e}")
    return [], {}


def save_progress(completed_ids: list[int], errors: dict, progress_file: str = PROGRESS_FILE) -> None:
    """Save current progress to JSON file."""
    try:
        data = {
            "completed_ids": sorted(list(set(completed_ids))),
            "total_completed": len(set(completed_ids)),
            "last_updated": datetime.now().isoformat(),
            "errors": errors,
        }
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de {progress_file}: {e}")


def get_executions_without_scores() -> pd.DataFrame:
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
            AND sc.methode = 'ragas'
            AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
        WHERE sc.id IS NULL
        ORDER BY e.date_execution DESC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    return df


def get_rag_chunks_for_scenario(scenario_id: int, prompt: str, departement: str) -> list[str]:
    """Retrieve RAG chunks for a scenario."""
    try:
        chunks = search_similar(
            query=prompt,
            departement=departement,
            top_k=4
        )
        if not chunks:
            logger.warning(f"Aucun chunk RAG trouve pour le scenario {scenario_id}")
        return chunks
    except Exception as e:
        logger.error(f"Erreur lors de la recuperation des chunks RAG pour le scenario {scenario_id}: {e}")
        return []


def save_ragas_scores(execution_id: int, scores_dict: dict) -> bool:
    """Save Ragas evaluation scores to database using direct SQL."""
    engine = create_engine(DATABASE_URL)
    
    try:
        metrics_to_save = {
            'faithfulness': scores_dict.get('faithfulness'),
            'answer_relevancy': scores_dict.get('answer_relevancy'),
            'context_precision': scores_dict.get('context_precision'),
            'context_recall': scores_dict.get('context_recall'),
        }
        
        valid_scores = [v for v in metrics_to_save.values() if v is not None]
        if not valid_scores:
            logger.warning(f"Aucun score valide a enregistrer pour l'execution {execution_id}")
            return False

        with engine.connect() as conn:
            for critere, note in metrics_to_save.items():
                if note is not None:
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
            logger.info(f"[OK] Sauvegarde de {len(valid_scores)} metriques pour l'execution {execution_id}")
            return True
        
    except Exception as e:
        logger.error(f"[ERR] Echec de sauvegarde pour l'execution {execution_id}: {e}")
        return False


def main():
    """Main re-evaluation logic with intelligent rate limiting and --resume support."""
    print("=" * 80)
    print("RAGAS RE-EVALUATION FOR MISSING SCORES")
    print("=" * 80)
    
    is_resume = "--resume" in sys.argv
    completed_ids, errors_dict = load_progress(PROGRESS_FILE)
    
    if is_resume:
        print(f"Mode --resume active. Chargement de {len(completed_ids)} IDs deja traites.")
    elif completed_ids:
        print(f"Fichier de progression detecte ({len(completed_ids)} IDs completes).")
        print("[INFO] Astuce : vous pouvez utiliser --resume pour ignorer ces executions.")
    
    # Etape 1 : Recuperer les executions orphelines
    print("\n1. Recherche des executions sans scores RAGAS...")
    df_missing = get_executions_without_scores()
    
    initial_missing_count = len(df_missing)
    print(f"   Trouve {initial_missing_count} executions orphelines en BDD.")
    
    if is_resume and completed_ids:
        df_missing = df_missing[~df_missing['execution_id'].isin(completed_ids)]
        print(f"   Apres filtrage du mode --resume : {len(df_missing)} executions restantes a evaluer.")
    
    total_to_process = len(df_missing)
    if total_to_process == 0:
        print("\n[SUCCESS] Toutes les executions ciblees sont deja evaluees !")
        return
    
    print(f"\n2. Debut de l'evaluation RAGAS de {total_to_process} executions...")
    print(f"   Modele juge : {MODELE_JUGE}")
    print("   Gestion du rate limit : pauses progressives de 5 min (300s) et 15 min (900s).")
    
    success_count = 0
    error_count = 0
    consecutive_rate_limits = 0
    rate_limit_blocked = False
    
    for idx, (_, row) in enumerate(df_missing.iterrows(), start=1):
        execution_id = int(row['execution_id'])
        scenario_id = int(row['scenario_id'])
        reponse = row['reponse_generee']
        question = row['prompt']
        sortie_attendue = row['sortie_attendue']
        departement = row['departement']
        model_name = row['model_name']
        
        print(f"\n   [{idx}/{total_to_process}] Exec {execution_id} | {model_name} ({departement})")
        
        max_exec_retries = 3
        exec_attempt = 0
        exec_success = False
        
        while exec_attempt < max_exec_retries and not exec_success:
            exec_attempt += 1
            try:
                chunks_rag = get_rag_chunks_for_scenario(scenario_id, question, departement)
                if not chunks_rag:
                    logger.warning(f"      Aucun chunk RAG pour l'exec {execution_id}")
                
                print(f"      Evaluation RAGAS (tentative {exec_attempt}/{max_exec_retries})...")
                
                f_res = evaluer_faithfulness(reponse, chunks_rag)
                time.sleep(1.0)
                ar_res = evaluer_answer_relevancy(reponse, question)
                time.sleep(1.0)
                cp_res = evaluer_context_precision(chunks_rag, question)
                time.sleep(1.0)
                cr_res = evaluer_context_recall(chunks_rag, sortie_attendue or "")
                time.sleep(1.0)
                
                scores_dict = {
                    'faithfulness': f_res.get('note'),
                    'answer_relevancy': ar_res.get('note'),
                    'context_precision': cp_res.get('note'),
                    'context_recall': cr_res.get('note'),
                }
                
                valid_count = sum(1 for v in scores_dict.values() if v is not None)
                if valid_count == 0:
                    raise Exception("Toutes les metriques ont retourne None (echec API / rate limit Groq)")
                
                print(f"      -> Faithfulness: {scores_dict.get('faithfulness', 'N/A')}")
                print(f"      -> Answer Relevancy: {scores_dict.get('answer_relevancy', 'N/A')}")
                print(f"      -> Context Precision: {scores_dict.get('context_precision', 'N/A')}")
                print(f"      -> Context Recall: {scores_dict.get('context_recall', 'N/A')}")
                
                if save_ragas_scores(execution_id, scores_dict):
                    success_count += 1
                    consecutive_rate_limits = 0
                    exec_success = True
                    if execution_id not in completed_ids:
                        completed_ids.append(execution_id)
                    save_progress(completed_ids, errors_dict)
                    print(f"      [OK] Exec {execution_id} sauvegardee avec succes.")
                else:
                    error_count += 1
                    errors_dict[str(execution_id)] = "Echec sauvegarde scores BDD"
                    break
                    
            except Exception as e:
                error_msg = str(e)
                is_rate_limit = (
                    "rate limit" in error_msg.lower()
                    or "429" in error_msg
                    or "tokens per day" in error_msg.lower()
                    or "tpd" in error_msg.lower()
                    or "otpm" in error_msg.lower()
                )
                
                if is_rate_limit:
                    consecutive_rate_limits += 1
                    if consecutive_rate_limits == 1:
                        print(f"\n[PAUSE 5 MIN] Rate limit Groq detecte sur Exec {execution_id}. Pause de 5 minutes avant reessai...")
                        logger.warning(f"Rate limit sur exec {execution_id}. Pause 5 min (300s).")
                        time.sleep(300)
                    elif consecutive_rate_limits == 2:
                        print(f"\n[PAUSE 15 MIN] Rate limit Groq persistant sur Exec {execution_id}. Pause longue de 15 minutes...")
                        logger.warning(f"Rate limit persistant sur exec {execution_id}. Pause 15 min (900s).")
                        time.sleep(900)
                    else:
                        print(f"\n[ERROR] Quota Groq epuise apres pauses de 5m et 15m.")
                        print(f"   Arret securise. Sauvegarde de l'etat dans {PROGRESS_FILE}...")
                        errors_dict[str(execution_id)] = f"Rate limit persistant : {error_msg[:100]}"
                        save_progress(completed_ids, errors_dict)
                        rate_limit_blocked = True
                        break
                else:
                    consecutive_rate_limits = 0
                    error_count += 1
                    errors_dict[str(execution_id)] = error_msg
                    logger.error(f"Erreur evaluation exec {execution_id}: {e}")
                    print(f"      [ERROR] Erreur : {error_msg[:100]}")
                    break
        
        if rate_limit_blocked:
            break
            
    # Resume
    print("\n" + "=" * 80)
    print("BILAN DE LA REEVALUATION")
    print("=" * 80)
    print(f"[OK] Evaluations reussies dans cette session : {success_count}/{total_to_process}")
    print(f"[ERROR] Erreurs rencontrees : {error_count}/{total_to_process}")
    print(f"[INFO] Total cumule complete : {len(completed_ids)}")
    
    remaining = total_to_process - success_count - error_count
    if remaining > 0 or rate_limit_blocked:
        print(f"[PAUSE] Restantes a traiter : {remaining}")
        print("\n[INFO] Pour reprendre plus tard une fois le quota Groq disponible :")
        print("   python reevaluate_missing_scores.py --resume")
        
    if success_count > 0:
        print("\n[INFO] Prochaines etapes :")
        print("   1. Actualisez le dashboard Streamlit")
        print("   2. Verifiez la disparition progressive du bandeau d'avertissement")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Interruption par l'utilisateur (Ctrl+C).")
        print("   Progression sauvegardee.")
        print("[INFO] Pour reprendre : python reevaluate_missing_scores.py --resume")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[FATAL ERROR] : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
