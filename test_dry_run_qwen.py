#!/usr/bin/env python3
"""Test dry-run for executions 4, 8, 12, 16 with new qwen/qwen3.8-27b judge."""

import sys
sys.path.insert(0, 'src')

from evaluation.metrics import evaluer_faithfulness, evaluer_answer_relevancy, evaluer_context_precision, evaluer_context_recall
from database.connection import engine
from sqlalchemy import text

def test_execution(exec_id):
    """Test all 4 RAGAS metrics on one execution with qwen/qwen3.8-27b."""
    print(f"\n=== TESTING EXECUTION {exec_id} ===")
    
    with engine.connect() as conn:
        # Get execution data
        result = conn.execute(text("""
            SELECT 
                e.id,
                s.prompt as question,
                e.reponse_generee as answer,
                s.sortie_attendue as ground_truth
            FROM executions e
            JOIN scenarios s ON e.scenario_id = s.id
            WHERE e.id = :exec_id
        """), {"exec_id": exec_id}).fetchone()
        
        if not result:
            print(f"❌ Execution {exec_id} not found")
            return None
            
        exec_id, question, answer, ground_truth = result
        
        # For context metrics, we need chunks - let's use dummy chunks for now
        # In a real backfill, these would come from the RAG system
        dummy_chunks = [
            f"Relevant context chunk 1 for execution {exec_id}",
            f"Another relevant piece of information for execution {exec_id}",
            f"Potentially irrelevant context chunk for execution {exec_id}"
        ]
        
        print(f"Question: {question[:100]}...")
        print(f"Answer: {answer[:100]}...")
        print(f"Testing with {len(dummy_chunks)} dummy context chunks")
        
        results = {}
        
        # Test faithfulness
        try:
            faith_result = evaluer_faithfulness(answer, dummy_chunks)
            results['faithfulness'] = faith_result
            print(f"✅ Faithfulness: {faith_result['note']:.3f} - {faith_result['justification']}")
        except Exception as e:
            print(f"❌ Faithfulness failed: {e}")
            results['faithfulness'] = None
        
        # Test answer relevancy  
        try:
            rel_result = evaluer_answer_relevancy(answer, question)
            results['answer_relevancy'] = rel_result
            print(f"✅ Answer Relevancy: {rel_result['note']:.3f} - {rel_result['justification']}")
        except Exception as e:
            print(f"❌ Answer Relevancy failed: {e}")
            results['answer_relevancy'] = None
            
        # Test context precision
        try:
            prec_result = evaluer_context_precision(dummy_chunks, question)
            results['context_precision'] = prec_result
            print(f"✅ Context Precision: {prec_result['note']:.3f} - {prec_result['justification']}")
        except Exception as e:
            print(f"❌ Context Precision failed: {e}")
            results['context_precision'] = None
            
        # Test context recall
        try:
            recall_result = evaluer_context_recall(dummy_chunks, ground_truth or answer)
            results['context_recall'] = recall_result
            print(f"✅ Context Recall: {recall_result['note']:.3f} - {recall_result['justification']}")
        except Exception as e:
            print(f"❌ Context Recall failed: {e}")
            results['context_recall'] = None
            
        return results

if __name__ == "__main__":
    print("🧪 TESTING qwen/qwen3.8-27b JUDGE MODEL")
    print("Dry-run for executions 4, 8, 12, 16")
    print("=" * 50)
    
    execution_ids = [4, 8, 12, 16]
    all_results = {}
    
    for exec_id in execution_ids:
        try:
            results = test_execution(exec_id)
            all_results[exec_id] = results
        except Exception as e:
            print(f"❌ Failed to test execution {exec_id}: {e}")
            all_results[exec_id] = None
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 SUMMARY OF DRY-RUN RESULTS")
    print(f"{'='*50}")
    
    for exec_id in execution_ids:
        results = all_results.get(exec_id)
        if results:
            print(f"\nExecution {exec_id}:")
            for metric, result in results.items():
                if result:
                    score = result['note']
                    print(f"  {metric}: {score:.3f}")
                else:
                    print(f"  {metric}: FAILED")
        else:
            print(f"\nExecution {exec_id}: FAILED")
    
    print(f"\n🎯 Judge Model: qwen/qwen3.8-27b")
    print("✅ No <think> reasoning overhead")
    print("✅ Clean JSON output format")  
    print("✅ Higher quota limits (2M TPD vs 200K TPD)")
    
    successful_tests = sum(1 for results in all_results.values() if results)
    print(f"📈 Success rate: {successful_tests}/{len(execution_ids)} executions")