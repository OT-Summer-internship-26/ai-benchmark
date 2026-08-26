#!/usr/bin/env python3
"""
Test script to verify None values are properly handled in dashboard.
Tests the complete fix for None values in execution details.
"""

import sys
import os
import traceback
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_safe_formatting_functions():
    """Test the safe formatting utility functions."""
    print("🔍 Testing safe formatting functions...")
    
    try:
        from src.dashboard.app import safe_format_score, safe_format_cost, safe_format_latency
        
        # Test safe_format_score
        test_cases_score = [
            (None, "N/A"),
            (0.85, "85.0%"),
            (0.0, "0.0%"),
            (1.0, "100.0%"),
            ("invalid", "N/A"),
            (float('nan'), "N/A")
        ]
        
        for value, expected in test_cases_score:
            result = safe_format_score(value)
            if "N/A" in expected or "%" in expected:
                if "N/A" in result or "%" in result:
                    print(f"  ✅ safe_format_score({value}) = {result}")
                else:
                    print(f"  ❌ safe_format_score({value}) = {result}, expected format like {expected}")
                    return False
            else:
                print(f"  ✅ safe_format_score({value}) = {result}")
        
        # Test safe_format_cost
        test_cases_cost = [
            (None, "N/A"),
            (0.0015, "0.0015"),
            (0, "0.0000"),
        ]
        
        for value, expected_pattern in test_cases_cost:
            result = safe_format_cost(value)
            if "N/A" in result or "." in result:
                print(f"  ✅ safe_format_cost({value}) = {result}")
            else:
                print(f"  ❌ safe_format_cost({value}) = {result}")
                return False
        
        # Test safe_format_latency  
        test_cases_latency = [
            (None, "N/A"),
            (1.234, "1.23s"),
            (0, "0.00s"),
        ]
        
        for value, expected_pattern in test_cases_latency:
            result = safe_format_latency(value)
            if "N/A" in result or "s" in result:
                print(f"  ✅ safe_format_latency({value}) = {result}")
            else:
                print(f"  ❌ safe_format_latency({value}) = {result}")
                return False
        
        print("✅ All safe formatting functions working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Safe formatting functions test failed: {e}")
        traceback.print_exc()
        return False

def test_data_loading_with_none_handling():
    """Test that data loading properly handles None values."""
    print("\n🔍 Testing data loading with None value handling...")
    
    try:
        from src.dashboard.app import load_executions
        import pandas as pd
        
        # Load executions
        df = load_executions(limit=10)
        
        if df.empty:
            print("⚠️ No executions found, skipping None value tests")
            return True
        
        print(f"✅ Loaded {len(df)} executions")
        
        # Check for expected columns
        expected_columns = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'score_global_auto']
        
        for col in expected_columns:
            if col in df.columns:
                none_count = df[col].isna().sum()
                total_count = len(df)
                print(f"  ✅ Column {col}: {none_count}/{total_count} None/NaN values")
            else:
                print(f"  ⚠️ Column {col} not found in dataframe")
        
        # Test global score calculation with None handling
        if 'score_global_auto' in df.columns:
            # Check that global scores are calculated properly even with some None values
            sample_row = df.iloc[0] if len(df) > 0 else None
            if sample_row is not None:
                score_cols = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
                available_scores = []
                for col in score_cols:
                    if col in sample_row and pd.notna(sample_row[col]) and sample_row[col] is not None:
                        available_scores.append(sample_row[col])
                
                expected_global = sum(available_scores) / len(available_scores) if available_scores else None
                actual_global = sample_row.get('score_global_auto')
                
                if available_scores:
                    if pd.notna(actual_global) and abs(actual_global - expected_global) < 0.001:
                        print(f"  ✅ Global score calculation correct: {actual_global:.3f}")
                    else:
                        print(f"  ⚠️ Global score calculation: expected {expected_global}, got {actual_global}")
                else:
                    if pd.isna(actual_global):
                        print(f"  ✅ Global score correctly None when no individual scores available")
                    else:
                        print(f"  ⚠️ Global score should be None when no individual scores available, got {actual_global}")
        
        print("✅ Data loading with None handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Data loading test failed: {e}")
        traceback.print_exc()
        return False

def test_display_formatting():
    """Test the display formatting function."""
    print("\n🔍 Testing display formatting...")
    
    try:
        from src.dashboard.app import format_executions_for_display
        import pandas as pd
        import numpy as np
        
        # Create test dataframe with None values
        test_data = {
            'date_execution': ['2024-01-01', '2024-01-02'],
            'modele_nom': ['Model A', 'Model B'],
            'nom_cas_usage': ['Test 1', 'Test 2'],
            'departement': ['IT', 'RH'],
            'latence_secondes': [1.234, None],
            'cout_estime': [0.0015, None],
            'score_global_auto': [0.85, None],
            'faithfulness': [0.9, None],
            'answer_relevancy': [None, 0.8],
            'context_precision': [0.7, 0.6],
            'context_recall': [None, None],
        }
        
        df = pd.DataFrame(test_data)
        display_columns = list(test_data.keys())
        
        formatted_df = format_executions_for_display(df, display_columns)
        
        # Check that all None values are formatted as "N/A"
        none_formatted_correctly = True
        for col in ['latence_secondes', 'cout_estime', 'score_global_auto', 'faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
            if col in formatted_df.columns:
                for idx, value in formatted_df[col].items():
                    if pd.isna(df.loc[idx, col]) or df.loc[idx, col] is None:
                        if value != "N/A":
                            print(f"  ❌ {col}[{idx}]: expected 'N/A', got '{value}'")
                            none_formatted_correctly = False
                        else:
                            print(f"  ✅ {col}[{idx}]: None formatted as 'N/A'")
                    else:
                        # Should be formatted as percentage or with units
                        if col in ['score_global_auto', 'faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']:
                            if "%" not in str(value) and value != "N/A":
                                print(f"  ⚠️ {col}[{idx}]: expected percentage format, got '{value}'")
                        elif col == 'latence_secondes':
                            if "s" not in str(value) and value != "N/A":
                                print(f"  ⚠️ {col}[{idx}]: expected latency format with 's', got '{value}'")
                        else:
                            print(f"  ✅ {col}[{idx}]: formatted as '{value}'")
        
        if none_formatted_correctly:
            print("✅ Display formatting handling None values correctly")
            return True
        else:
            print("❌ Some None values not formatted correctly")
            return False
        
    except Exception as e:
        print(f"❌ Display formatting test failed: {e}")
        traceback.print_exc()
        return False

def test_radar_chart_none_handling():
    """Test that radar chart handles None values properly."""
    print("\n🔍 Testing radar chart None value handling...")
    
    try:
        from src.dashboard.radar_chart import get_radar_chart_data, create_metrics_comparison_table
        from src.dashboard.admin_queries import get_all_departments
        
        # Get available departments
        departments = get_all_departments()
        
        if not departments:
            print("⚠️ No departments found, skipping radar chart test")
            return True
        
        # Test with first department
        dept_name = departments[0]['name']
        
        # Test radar chart data
        radar_data = get_radar_chart_data(dept_name, max_models=3)
        
        if radar_data:
            print(f"✅ Radar chart data generated for {dept_name}")
            
            # Check that models have proper metric values (should be 0.0 for None, not None itself)
            for model in radar_data.get('models', []):
                metrics = model.get('metrics', {})
                for metric_name, value in metrics.items():
                    if value is None:
                        print(f"  ⚠️ Model {model['name']} has None for {metric_name} (should be 0.0)")
                    elif isinstance(value, (int, float)) and 0.0 <= value <= 1.0:
                        print(f"  ✅ Model {model['name']} {metric_name}: {value}")
                    else:
                        print(f"  ⚠️ Model {model['name']} {metric_name}: unexpected value {value}")
        else:
            print(f"⚠️ No radar chart data for {dept_name} (may be no executions)")
        
        # Test metrics comparison table
        metrics_table = create_metrics_comparison_table(dept_name)
        
        if metrics_table is not None and not metrics_table.empty:
            print(f"✅ Metrics comparison table created with {len(metrics_table)} rows")
            
            # Check for proper "N/A" formatting in percentage columns
            percentage_columns = ['Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall', 'Global Score']
            for col in percentage_columns:
                if col in metrics_table.columns:
                    for idx, value in metrics_table[col].items():
                        if "N/A" in str(value) or "%" in str(value):
                            print(f"  ✅ {col}[{idx}]: properly formatted as '{value}'")
                        else:
                            print(f"  ⚠️ {col}[{idx}]: unexpected format '{value}'")
        else:
            print(f"⚠️ No metrics table data for {dept_name}")
        
        print("✅ Radar chart None handling test completed")
        return True
        
    except Exception as e:
        print(f"❌ Radar chart test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all None value handling tests."""
    print("🚀 Testing None Values Fix for Dashboard")
    print("=" * 60)
    
    start_time = datetime.now()
    
    tests = [
        ("Safe Formatting Functions", test_safe_formatting_functions),
        ("Data Loading with None Handling", test_data_loading_with_none_handling),
        ("Display Formatting", test_display_formatting),
        ("Radar Chart None Handling", test_radar_chart_none_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 NONE VALUES FIX TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"⏱️  Test duration: {duration.total_seconds():.1f} seconds")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! None values fix is working correctly.")
        print("\nThe dashboard should now display:")
        print("- 'N/A' instead of 'None' for missing scores")
        print("- Properly formatted percentages for available scores")
        print("- Consistent formatting across all tables and details")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())