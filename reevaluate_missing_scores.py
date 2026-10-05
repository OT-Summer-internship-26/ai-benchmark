"""
Re-evaluate executions with RAGAS scores using the current judge model.

Changes vs the original (Task 3 spec):
  - --all flag: bypasses the HAVING COUNT < 4 filter, re-evaluates ALL executions
  - save_ragas_scores: writes ONLY when ALL 4 RAGAS metrics are non-None
  - save_ragas_scores: DELETE old ragas rows + INSERT new ones in ONE transaction
    (including score_global = mean of the 4)
  - Backs up reevaluation_progress.json before resetting it at run start
  - Supports --limit and --resume
"""

import sys
import io
import json
import time
import shutil
from datetime import datetime
from pathlib import Path

import functools
# Force unbuffered prints so real-time output is immediately visible
print = functools.partial(print, flush=True)

# Force UTF-8 standard output and error streams
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
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
REQUIRED_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


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


def backup_and_reset_progress(progress_file: str = PROGRESS_FILE) -> None:
    """Back up the progress file and reset it before a fresh run."""
    path = Path(progress_file)
    if path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f".backup_{ts}.json")
        shutil.copy2(path, backup_path)
        print(f"   [BACKUP] {progress_file} sauvegarde dans {backup_path}")
    # Reset to empty state
    save_progress([], {}, progress_file)
    print(f"   [RESET] {progress_file} reinitialise.")


def get_executions_without_scores(all_mode: bool = False) -> pd.DataFrame:
    """
    Find executions to re-evaluate.

    all_mode=False (default): only those with fewer than 4 RAGAS metric scores
    all_mode=True  (--all):   ALL executions, regardless of existing score count
    """
    engine = create_engine(DATABASE_URL)

    if all_mode:
        # Return ALL executions unconditionally
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
            WHERE e.reponse_generee IS NOT NULL
              AND e.reponse_generee != ''
            ORDER BY e.date_execution DESC
        """)
    else:
        # Legacy: only those missing at least one of the 4 RAGAS metrics
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
                AND COALESCE(sc.is_legacy, FALSE) = FALSE
                AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
            GROUP BY e.id, e.scenario_id, e.reponse_generee, s.prompt, s.sortie_attendue, s.departement, m.nom, e.date_execution
            HAVING COUNT(DISTINCT sc.critere) < 4
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
    """
    Save Ragas evaluation scores to database in ONE transaction.

    CRITICAL: Only writes if ALL 4 RAGAS metrics are non-None.
    Deletes old non-legacy ragas rows for this execution, then inserts
    all 4 metrics + score_global in a single committed transaction.

    Returns True on success, False otherwise.
    """
    engine = create_engine(DATABASE_URL)

    # Validate: all 4 required metrics must be non-None
    missing_metrics = [m for m in REQUIRED_METRICS if scores_dict.get(m) is None]
    if missing_metrics:
        logger.warning(
            f"[SKIP] Execution {execution_id}: metriques manquantes = {missing_metrics}. "
            "Aucune ecriture en base (regles: toutes les 4 metriques requises)."
        )
        return False

    try:
        # Compute global score = arithmetic mean of all 4 metrics
        valid_scores = [scores_dict[m] for m in REQUIRED_METRICS]
        score_global = round(sum(valid_scores) / len(valid_scores), 6)

        with engine.begin() as conn:  # begin() auto-commits or rolls back on exception
            # Step 1: DELETE all old non-legacy ragas rows for this execution
            conn.execute(text("""
                DELETE FROM scores
                WHERE execution_id = :exec_id
                  AND methode = 'ragas'
                  AND COALESCE(is_legacy, FALSE) = FALSE
            """), {"exec_id": execution_id})

            # Step 2: INSERT the 4 metric rows
            for critere in REQUIRED_METRICS:
                note = scores_dict[critere]
                conn.execute(text("""
                    INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                    VALUES (:exec_id, :critere, :note, :comment, 'ragas', FALSE)
                """), {
                    "exec_id": execution_id,
                    "critere": critere,
                    "note": note,
                    "comment": f"Re-evaluated by {MODELE_JUGE}",
                })

            # Step 3: INSERT score_global
            conn.execute(text("""
                INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                VALUES (:exec_id, 'score_global', :note, :comment, 'ragas', FALSE)
            """), {
                "exec_id": execution_id,
                "note": score_global,
                "comment": f"Mean of 4 RAGAS metrics (judge: {MODELE_JUGE})",
            })
            # engine.begin() auto-commits here

        logger.info(
            f"[OK] Exec {execution_id}: 5 rows saved "
            f"(f={scores_dict['faithfulness']:.3f}, "
            f"ar={scores_dict['answer_relevancy']:.3f}, "
            f"cp={scores_dict['context_precision']:.3f}, "
            f"cr={scores_dict['context_recall']:.3f}, "
            f"global={score_global:.3f})"
        )
        return True

    except Exception as e:
        logger.error(f"[ERR] Echec de sauvegarde pour l'execution {execution_id}: {e}")
        return False


def main():
    """Main re-evaluation logic with --all, --limit, and --resume support."""
    print("=" * 80)
    print("RAGAS RE-EVALUATION")
    print("=" * 80)

    is_all = "--all" in sys.argv
    is_resume = "--resume" in sys.argv

    # --all without --resume resets the progress file
    if is_all and not is_resume:
        print("\n[INFO] Mode --all active (bypass HAVING COUNT < 4 filter).")
        print("[INFO] Sauvegarde et reinitialisation du fichier de progression...")
        backup_and_reset_progress(PROGRESS_FILE)

    completed_ids, errors_dict = load_progress(PROGRESS_FILE)

    if is_resume:
        print(f"[INFO] Mode --resume active. Chargement de {len(completed_ids)} IDs deja traites.")
    elif completed_ids and not is_all:
        print(f"[INFO] Fichier de progression detecte ({len(completed_ids)} IDs completes).")
        print("       Astuce : vous pouvez utiliser --resume pour ignorer ces executions.")

    # Etape 1: Recuperer les executions
    mode_label = "TOUTES (--all)" if is_all else "manquantes (COUNT < 4)"
    print(f"\n1. Recherche des executions {mode_label}...")
    df_missing = get_executions_without_scores(all_mode=is_all)

    initial_count = len(df_missing)
    print(f"   Trouve {initial_count} executions en BDD.")

    if is_resume and completed_ids:
        df_missing = df_missing[~df_missing['execution_id'].isin(completed_ids)]
        print(f"   Apres filtrage --resume : {len(df_missing)} executions restantes.")

    # Support --dept filter
    dept_filter = None
    if "--dept" in sys.argv:
        try:
            dept_idx = sys.argv.index("--dept")
            dept_filter = sys.argv[dept_idx + 1]
        except (ValueError, IndexError):
            print("   [WARN] --dept specifie sans valeur. Ignore.")
        if dept_filter:
            df_missing = df_missing[df_missing['departement'] == dept_filter]
            print(f"   [DEPT] Filtrage sur departement = '{dept_filter}' : {len(df_missing)} executions.")

    # Support --limit flag
    limit_count = None
    if "--limit" in sys.argv:
        try:
            lim_idx = sys.argv.index("--limit")
            limit_count = int(sys.argv[lim_idx + 1])
        except (ValueError, IndexError):
            limit_count = 1
        df_missing = df_missing.head(limit_count)
        print(f"   [LIMIT] Restriction aux {limit_count} premiere(s) execution(s).")

    total_to_process = len(df_missing)
    if total_to_process == 0:
        print("\n[SUCCESS] Toutes les executions ciblees sont deja evaluees !")
        return

    print(f"\n2. Debut de l'evaluation RAGAS de {total_to_process} executions...")
    print(f"   Modele juge   : {MODELE_JUGE}")
    print(f"   Mode          : {'--all (toutes executions)' if is_all else 'executions incompletes'}")
    print(f"   Regles write  : SEULEMENT si les 4 metriques sont non-None")
    print("   Rate limiting : pauses progressives de 5 min (300s) et 15 min (900s).")

    success_count = 0
    skip_count = 0
    error_count = 0
    consecutive_rate_limits = 0
    rate_limit_blocked = False

    for idx, (_, row) in enumerate(df_missing.iterrows(), start=1):
        execution_id = int(row['execution_id'])
        scenario_id = int(row['scenario_id'])
        reponse = row['reponse_generee']
        question = row['prompt']
        sortie_attendue = row.get('sortie_attendue') or ""
        departement = row['departement']
        model_name = row['model_name']

        print(f"\n   [{idx:>3}/{total_to_process}] Exec {execution_id:>4} | {model_name} ({departement})")

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
                cr_res = evaluer_context_recall(chunks_rag, sortie_attendue)
                time.sleep(1.0)

                scores_dict = {
                    'faithfulness': f_res.get('note'),
                    'answer_relevancy': ar_res.get('note'),
                    'context_precision': cp_res.get('note'),
                    'context_recall': cr_res.get('note'),
                }

                print(f"      -> Faithfulness      : {scores_dict.get('faithfulness', 'None')}")
                print(f"      -> Answer Relevancy  : {scores_dict.get('answer_relevancy', 'None')}")
                print(f"      -> Context Precision : {scores_dict.get('context_precision', 'None')}")
                print(f"      -> Context Recall    : {scores_dict.get('context_recall', 'None')}")

                # All-None check: if truly quota exhausted, bail
                all_none = all(v is None for v in scores_dict.values())
                if all_none:
                    raise Exception("Toutes les metriques ont retourne None (echec API / rate limit Groq)")

                # save_ragas_scores will skip if any metric is None
                if save_ragas_scores(execution_id, scores_dict):
                    success_count += 1
                    consecutive_rate_limits = 0
                    exec_success = True
                    if execution_id not in completed_ids:
                        completed_ids.append(execution_id)
                    save_progress(completed_ids, errors_dict)
                    print(f"      [OK] Exec {execution_id} sauvegardee avec succes.")
                else:
                    # Metrics were computed but some are None — skip without error
                    skip_count += 1
                    exec_success = True  # don't retry
                    errors_dict[str(execution_id)] = "Metriques partielles (< 4 non-None) — non ecrit"
                    save_progress(completed_ids, errors_dict)
                    print(f"      [SKIP] Exec {execution_id}: metriques incompletes — non ecrit.")

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
                        print(f"\n[PAUSE 5 MIN] Rate limit Groq sur Exec {execution_id}. Pause 5 minutes...")
                        logger.warning(f"Rate limit sur exec {execution_id}. Pause 5 min (300s).")
                        time.sleep(300)
                    elif consecutive_rate_limits == 2:
                        print(f"\n[PAUSE 15 MIN] Rate limit persistant sur Exec {execution_id}. Pause 15 minutes...")
                        logger.warning(f"Rate limit persistant exec {execution_id}. Pause 15 min (900s).")
                        time.sleep(900)
                    else:
                        print(f"\n[ERROR] Quota Groq epuise (apres pauses 5m + 15m). Arret securise.")
                        errors_dict[str(execution_id)] = f"Rate limit persistant: {error_msg[:100]}"
                        save_progress(completed_ids, errors_dict)
                        rate_limit_blocked = True
                        break
                else:
                    consecutive_rate_limits = 0
                    error_count += 1
                    errors_dict[str(execution_id)] = error_msg
                    logger.error(f"Erreur evaluation exec {execution_id}: {e}")
                    print(f"      [ERROR] Erreur: {error_msg[:120]}")
                    break

        if rate_limit_blocked:
            break

    # Final summary
    print("\n" + "=" * 80)
    print("BILAN DE LA REEVALUATION")
    print("=" * 80)
    print(f"[OK]   Evaluations sauvegardees dans cette session : {success_count}/{total_to_process}")
    print(f"[SKIP] Metriques incompletes (< 4 non-None) ignorees: {skip_count}/{total_to_process}")
    print(f"[ERR]  Erreurs rencontrees                           : {error_count}/{total_to_process}")
    print(f"[INFO] Total cumule complete (progress file)         : {len(completed_ids)}")

    if rate_limit_blocked:
        remaining = total_to_process - success_count - skip_count - error_count
        print(f"\n[PAUSE] Quota Groq epuise. Executions restantes : {remaining}")
        print("\n[INFO] Pour reprendre une fois le quota Groq restaure :")
        if is_all:
            print("   python reevaluate_missing_scores.py --all --resume")
        else:
            print("   python reevaluate_missing_scores.py --resume")

    if success_count > 0:
        # Post-run: show remaining None per metric per department
        print("\n[INFO] Analyse des None restants par metrique et departement...")
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        s.departement,
                        sc.critere,
                        COUNT(*) FILTER (WHERE sc.note IS NULL) AS none_count,
                        COUNT(*) AS total_count
                    FROM executions e
                    JOIN scenarios s ON e.scenario_id = s.id
                    LEFT JOIN scores sc ON sc.execution_id = e.id
                        AND sc.methode = 'ragas'
                        AND COALESCE(sc.is_legacy, FALSE) = FALSE
                        AND sc.critere IN ('faithfulness', 'answer_relevancy', 'context_precision', 'context_recall')
                    GROUP BY s.departement, sc.critere
                    ORDER BY s.departement, sc.critere
                """)).fetchall()

                if rows:
                    print(f"\n  {'Departement':<32} | {'Metrique':<22} | None | Total")
                    print(f"  {'-'*32}-+-{'-'*22}-+------+------")
                    for dept, critere, none_c, total_c in rows:
                        critere_str = critere or "(null)"
                        print(f"  {dept:<32} | {critere_str:<22} | {none_c:>4} | {total_c:>5}")
        except Exception as e:
            print(f"   [WARN] Impossible de lire les None restants: {e}")

    print("\n[INFO] Prochaines etapes :")
    print("   1. Verifiez le dashboard Streamlit (metriques RAGAS mises a jour)")
    print("   2. Verifiez l'absence de doublons: SELECT execution_id, critere, COUNT(*)")
    print("      FROM scores WHERE methode='ragas' GROUP BY 1,2 HAVING COUNT(*) > 1;")


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
