"""
Re-evaluate executions with INCOMPLETE RAGAS scores (missing any of the 4 core metrics).
This script will:
1. Find executions missing any of: faithfulness, answer_relevancy, context_precision, context_recall
2. DELETE existing incomplete RAGAS scores for those executions
3. Re-run full RAGAS evaluation with Ollama fallback
4. Insert complete scores into database
"""
import sys
import os
import argparse
from datetime import datetime
from sqlalchemy import text
from src.database.connection import engine
from src.evaluation.deepeval_runner import evaluer_execution_ragas
from src.rag.vector_store import search_similar
from src.evaluation.metrics import get_active_judge_name
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def get_scenario(scenario_id: int) -> dict:
    """Fetch scenario from database"""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, departement, prompt, sortie_attendue
                FROM scenarios
                WHERE id = :scenario_id
            """),
            {"scenario_id": scenario_id}
        ).fetchone()
        
        if not result:
            return None
            
        return {
            "id": result.id,
            "departement": result.departement,
            "prompt": result.prompt,
            "sortie_attendue": result.sortie_attendue,
        }


def get_executions_with_incomplete_scores(date_filter: str = None) -> list[dict]:
    """
    Find executions with incomplete RAGAS scores.
    An execution is incomplete if it's missing any of the 4 core metrics:
    - faithfulness
    - answer_relevancy
    - context_precision
    - context_recall
    """
    query = """
        WITH ragas_scores AS (
            SELECT 
                execution_id,
                COUNT(DISTINCT CASE WHEN critere = 'faithfulness' THEN critere END) as has_faithfulness,
                COUNT(DISTINCT CASE WHEN critere = 'answer_relevancy' THEN critere END) as has_answer_relevancy,
                COUNT(DISTINCT CASE WHEN critere = 'context_precision' THEN critere END) as has_context_precision,
                COUNT(DISTINCT CASE WHEN critere = 'context_recall' THEN critere END) as has_context_recall
            FROM scores
            WHERE methode = 'ragas' AND is_legacy = FALSE
            GROUP BY execution_id
        )
        SELECT 
            e.id,
            e.scenario_id,
            e.modele_id,
            e.reponse_generee,
            e.date_execution,
            m.nom as modele_nom,
            COALESCE(rs.has_faithfulness, 0) as has_faithfulness,
            COALESCE(rs.has_answer_relevancy, 0) as has_answer_relevancy,
            COALESCE(rs.has_context_precision, 0) as has_context_precision,
            COALESCE(rs.has_context_recall, 0) as has_context_recall
        FROM executions e
        LEFT JOIN modeles m ON m.id = e.modele_id
        LEFT JOIN ragas_scores rs ON rs.execution_id = e.id
    """
    
    if date_filter:
        query += f" WHERE e.date_execution >= '{date_filter}'"
    
    query += """
        GROUP BY e.id, e.scenario_id, e.modele_id, e.reponse_generee, e.date_execution, m.nom,
                 rs.has_faithfulness, rs.has_answer_relevancy, rs.has_context_precision, rs.has_context_recall
        HAVING 
            COALESCE(rs.has_faithfulness, 0) = 0 OR
            COALESCE(rs.has_answer_relevancy, 0) = 0 OR
            COALESCE(rs.has_context_precision, 0) = 0 OR
            COALESCE(rs.has_context_recall, 0) = 0
        ORDER BY e.date_execution DESC
    """
    
    with engine.connect() as conn:
        results = conn.execute(text(query)).fetchall()
        
    return [{
        "execution_id": r.id,
        "scenario_id": r.scenario_id,
        "modele_id": r.modele_id,
        "reponse": r.reponse_generee,
        "date_execution": r.date_execution,
        "modele_nom": r.modele_nom,
        "missing_metrics": [
            "faithfulness" if r.has_faithfulness == 0 else None,
            "answer_relevancy" if r.has_answer_relevancy == 0 else None,
            "context_precision" if r.has_context_precision == 0 else None,
            "context_recall" if r.has_context_recall == 0 else None,
        ]
    } for r in results]


def delete_existing_ragas_scores(execution_id: int):
    """Delete ALL existing RAGAS scores for an execution before re-evaluating"""
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                DELETE FROM scores
                WHERE execution_id = :exec_id
                AND methode = 'ragas'
                AND is_legacy = FALSE
            """),
            {"exec_id": execution_id}
        )
        deleted = result.rowcount
        logger.info(f"  🗑️  Deleted {deleted} existing RAGAS scores for execution {execution_id}")
        return deleted


def insert_scores(execution_id: int, resultat: dict):
    """Insert evaluation results into scores table"""
    criteres_a_inserer = {
        "faithfulness": resultat.get("faithfulness", {}),
        "answer_relevancy": resultat.get("answer_relevancy", {}),
        "context_precision": resultat.get("context_precision", {}),
        "context_recall": resultat.get("context_recall", {}),
        "toxicity": resultat.get("toxicity", {}),
        "harmfulness": resultat.get("harmfulness", {}),
    }
    
    with engine.begin() as conn:
        nb_inseres = 0
        for critere, detail in criteres_a_inserer.items():
            if not detail or detail.get("note") is None:
                logger.warning(f"  ⚠️  {critere} returned None - skipping")
                continue
                
            conn.execute(
                text("""
                    INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                    VALUES (:exec_id, :critere, :note, :commentaire, 'ragas', FALSE)
                """),
                {
                    "exec_id": execution_id,
                    "critere": critere,
                    "note": float(detail["note"]),
                    "commentaire": str(detail.get("justification", ""))[:500],
                }
            )
            nb_inseres += 1
        
        # Insert score_global
        if resultat.get("score_global") is not None:
            conn.execute(
                text("""
                    INSERT INTO scores (execution_id, critere, note, commentaire, methode, is_legacy)
                    VALUES (:exec_id, :critere, :note, :commentaire, 'ragas', FALSE)
                """),
                {
                    "exec_id": execution_id,
                    "critere": "score_global",
                    "note": float(resultat["score_global"]),
                    "commentaire": "Moyenne des métriques Ragas disponibles",
                }
            )
            nb_inseres += 1
            
        logger.info(f"  ✅ {nb_inseres} scores inserted for execution {execution_id}")
        return nb_inseres


def main():
    parser = argparse.ArgumentParser(description="Re-evaluate executions with incomplete RAGAS scores")
    parser.add_argument('--auto', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--all', action='store_true', help='Re-evaluate all incomplete executions (no date filter)')
    parser.add_argument('--today', action='store_true', help='Re-evaluate only today\'s incomplete executions')
    parser.add_argument('--resume', action='store_true', help='Alias for --auto (resume without prompt)')
    args = parser.parse_args()
    
    # --resume is an alias for --auto
    if args.resume:
        args.auto = True
    
    print("=" * 80)
    print("RE-EVALUATION OF EXECUTIONS WITH INCOMPLETE RAGAS SCORES")
    print("=" * 80)
    print()
    
    # Get active judge configuration
    active_judge = get_active_judge_name()
    print(f"🤖 Active judge: {active_judge}")
    print()
    
    # Determine date filter
    date_filter = None
    if args.today:
        date_filter = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Filtering: Today's executions only ({date_filter})")
    elif not args.all:
        date_filter = "2026-10-05"  # Default to today's date
        print(f"📅 Filtering: Executions from {date_filter} onwards")
    else:
        print(f"📅 No date filter: Processing ALL incomplete executions")
    print()
    
    # Find executions with incomplete scores
    print("🔍 Searching for executions with incomplete RAGAS scores...")
    executions = get_executions_with_incomplete_scores(date_filter=date_filter)
    
    if not executions:
        print("✅ All executions already have complete RAGAS scores!")
        return
    
    print(f"Found {len(executions)} executions with incomplete scores:")
    print()
    for exec_data in executions[:5]:  # Show first 5
        missing = [m for m in exec_data["missing_metrics"] if m]
        print(f"  - Execution {exec_data['execution_id']}: missing {', '.join(missing)}")
    if len(executions) > 5:
        print(f"  ... and {len(executions) - 5} more")
    print()
    
    # Confirm before proceeding
    if not args.auto:
        response = input(f"⚠️  This will DELETE existing partial scores and re-evaluate. Proceed? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    print()
    print("=" * 80)
    print("STARTING RE-EVALUATION WITH SCORE DELETION")
    print("=" * 80)
    print()
    
    success_count = 0
    error_count = 0
    
    for idx, execution in enumerate(executions, 1):
        exec_id = execution["execution_id"]
        scenario_id = execution["scenario_id"]
        missing = [m for m in execution["missing_metrics"] if m]
        
        print(f"\n[{idx}/{len(executions)}] Execution {exec_id} (scenario {scenario_id}, model: {execution['modele_nom']})")
        print(f"  Date: {execution['date_execution']}")
        print(f"  Missing: {', '.join(missing)}")
        
        try:
            # DELETE existing partial scores
            deleted = delete_existing_ragas_scores(exec_id)
            
            # Fetch scenario
            scenario = get_scenario(scenario_id)
            if not scenario:
                logger.error(f"  ❌ Scenario {scenario_id} not found!")
                error_count += 1
                continue
            
            print(f"  Department: {scenario['departement']}")
            
            # Fetch RAG chunks
            print(f"  Fetching RAG context...", end=" ")
            chunks_rag = search_similar(scenario["prompt"], scenario["departement"], top_k=3)
            print(f"✓ ({len(chunks_rag)} chunks)")
            
            if not chunks_rag:
                logger.warning(f"  ⚠️  No RAG chunks found for scenario {scenario_id}")
            
            # Evaluate
            print(f"  Evaluating with {active_judge}...")
            resultat = evaluer_execution_ragas(
                reponse=execution["reponse"],
                question=scenario["prompt"],
                contexte_chunks=chunks_rag,
                sortie_attendue=scenario.get("sortie_attendue"),
            )
            
            # Display results
            print(f"    Faithfulness:       {resultat.get('faithfulness', {}).get('note', 'N/A')}")
            print(f"    Answer relevancy:   {resultat.get('answer_relevancy', {}).get('note', 'N/A')}")
            print(f"    Context precision:  {resultat.get('context_precision', {}).get('note', 'N/A')}")
            print(f"    Context recall:     {resultat.get('context_recall', {}).get('note', 'N/A')}")
            print(f"    Score global:       {resultat.get('score_global', 'N/A')}")
            
            # Insert scores
            nb_inserted = insert_scores(exec_id, resultat)
            
            # Verify we have all 4 core metrics
            core_metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
            missing_after = [m for m in core_metrics if resultat.get(m, {}).get('note') is None]
            
            if missing_after:
                logger.warning(f"  ⚠️  Still missing after re-evaluation: {', '.join(missing_after)}")
                error_count += 1
            elif nb_inserted >= 5:  # At least 4 core + score_global
                success_count += 1
            else:
                logger.warning(f"  ⚠️  Only {nb_inserted} scores inserted (expected at least 5)")
                error_count += 1
                
        except Exception as e:
            logger.error(f"  ❌ Error evaluating execution {exec_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
    
    print()
    print("=" * 80)
    print("RE-EVALUATION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully re-evaluated: {success_count} executions")
    print(f"❌ Errors/Incomplete: {error_count} executions")
    print()
    
    # Final verification
    print("🔍 Verifying results...")
    remaining = get_executions_with_incomplete_scores(date_filter=date_filter)
    if remaining:
        print(f"⚠️  {len(remaining)} executions still have incomplete scores:")
        for exec_data in remaining[:5]:
            missing = [m for m in exec_data["missing_metrics"] if m]
            print(f"  - Execution {exec_data['execution_id']}: missing {', '.join(missing)}")
    else:
        print("✅ All executions now have complete RAGAS scores!")


if __name__ == "__main__":
    main()
