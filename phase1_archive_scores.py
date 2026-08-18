#!/usr/bin/env python3
"""
Phase 1: Archive legacy scores with is_legacy flag
Does NOT delete, only archives for safety
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text, inspect
from src.database.connection import engine

def main():
    print('\nPHASE 1 - ARCHIVING LEGACY SCORES')
    print('='*70)

    with engine.begin() as conn:
        # Step 1: Check if column exists
        print('\n1. Checking schema...')
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('scores')]
        
        if 'is_legacy' not in columns:
            print('   Adding is_legacy column...')
            conn.execute(text('ALTER TABLE scores ADD COLUMN is_legacy BOOLEAN DEFAULT FALSE'))
            print('   ✓ Column added')
        else:
            print('   ✓ is_legacy column already exists')

        # Step 2: Tag legacy scores
        print('\n2. Tagging legacy scores...')
        
        # Count BEFORE
        before = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = TRUE')).scalar()
        print(f'   Before: {before} scores marked as legacy')
        
        # Update: heuristic criteria
        result1 = conn.execute(text(
            "UPDATE scores SET is_legacy = TRUE WHERE critere IN ('completude','structure','fidelite_rag','honnetete')"
        ))
        print(f'   ✓ Tagged {result1.rowcount} rows with heuristic criteria')
        
        # Update: score_global > 1.0 (old scale)
        result2 = conn.execute(text(
            "UPDATE scores SET is_legacy = TRUE WHERE critere='score_global' AND note > 1.0"
        ))
        print(f'   ✓ Tagged {result2.rowcount} rows with score_global > 1.0')
        
        # Count AFTER
        after = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = TRUE')).scalar()
        print(f'   After: {after} scores marked as legacy')
        print(f'   Total newly tagged: {after - before}')
        
        # Step 3: Count modern Ragas scores
        print('\n3. Verifying modern Ragas scores...')
        ragas_count = conn.execute(text(
            "SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE AND critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')"
        )).scalar()
        print(f'   ✓ {ragas_count} modern Ragas scores present')
        
        # Step 4: Summary
        print('\n4. Score distribution summary...')
        total = conn.execute(text('SELECT COUNT(*) FROM scores')).scalar()
        legacy_count = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = TRUE')).scalar()
        modern_count = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE')).scalar()
        
        print(f'   Total scores: {total}')
        print(f'   - Legacy (is_legacy=TRUE): {legacy_count}')
        print(f'   - Modern (is_legacy=FALSE): {modern_count}')
        if total > 0:
            print(f'   - Ratio: {legacy_count}/{total} = {100*legacy_count/total:.1f}% legacy')
        
        # Step 5: Sample legacy criteria
        print('\n5. Sample legacy score rows (showing criteria names)...')
        legacy_rows = conn.execute(text(
            "SELECT DISTINCT critere FROM scores WHERE is_legacy = TRUE ORDER BY critere LIMIT 10"
        )).fetchall()
        for row in legacy_rows:
            print(f'   - {row[0]}')
        
        # Step 6: Verify data integrity
        print('\n6. Data integrity checks...')
        
        # Check: no NULL is_legacy values
        nulls = conn.execute(text('SELECT COUNT(*) FROM scores WHERE is_legacy IS NULL')).scalar()
        if nulls == 0:
            print('   ✓ No NULL is_legacy values')
        else:
            print(f'   ⚠ WARNING: {nulls} NULL is_legacy values found')
        
        # Check: all heuristic scores are marked legacy
        unmarked_heur = conn.execute(text(
            "SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE AND critere IN ('completude','structure','fidelite_rag','honnetete')"
        )).scalar()
        if unmarked_heur == 0:
            print('   ✓ All heuristic criteria marked as legacy')
        else:
            print(f'   ⚠ WARNING: {unmarked_heur} heuristic scores NOT marked as legacy')
        
        # Check: all score_global > 1.0 are marked legacy
        unmarked_old_scale = conn.execute(text(
            "SELECT COUNT(*) FROM scores WHERE is_legacy = FALSE AND critere='score_global' AND note > 1.0"
        )).scalar()
        if unmarked_old_scale == 0:
            print('   ✓ All old-scale scores (>1.0) marked as legacy')
        else:
            print(f'   ⚠ WARNING: {unmarked_old_scale} old-scale scores NOT marked as legacy')

    print('\n✓ PHASE 1 STEP 1-2 COMPLETE: Legacy scores archived')
    print('='*70 + '\n')
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
