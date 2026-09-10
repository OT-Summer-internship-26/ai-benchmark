"""Check PostgreSQL table structure"""
from sqlalchemy import create_engine, text, inspect
from src.config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL)

print("=" * 80)
print("POSTGRESQL TABLE STRUCTURES")
print("=" * 80)

inspector = inspect(engine)

for table_name in ['executions', 'scores', 'scenarios', 'modeles']:
    print(f"\n📋 Table: {table_name}")
    print("-" * 80)
    
    try:
        columns = inspector.get_columns(table_name)
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  {col['name']:30s} {str(col['type']):20s} {nullable}")
            
        # Count rows
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"\n  → {count} rows")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Check scores table data
print("\n" + "=" * 80)
print("SCORES TABLE DATA SAMPLE")
print("=" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            s.id,
            s.execution_id,
            s.faithfulness,
            s.answer_relevancy,
            s.context_precision,
            s.context_recall,
            s.score_global_auto,
            s.methode
        FROM scores s
        ORDER BY s.id DESC
        LIMIT 10
    """))
    
    print("\nLast 10 scores:")
    for row in result.fetchall():
        print(f"  ID:{row[0]:3d} Exec:{row[1]:3d} | F:{row[2]} AR:{row[3]} CP:{row[4]} CR:{row[5]} | Global:{row[6]} | Method:{row[7]}")
        
    # Statistics
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(faithfulness) as with_faith,
            COUNT(answer_relevancy) as with_ar,
            COUNT(methode) as with_method,
            methode,
            COUNT(*) as count_per_method
        FROM scores
        GROUP BY methode
    """))
    
    print("\n" + "=" * 80)
    print("SCORES STATISTICS")
    print("=" * 80)
    for row in result.fetchall():
        print(f"  Method: {row[4]:15s} → {row[5]:3d} scores")
