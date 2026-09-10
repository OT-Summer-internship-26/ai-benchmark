"""Test PostgreSQL connection and check data"""
import sys
from sqlalchemy import create_engine, text
from src.config.settings import DATABASE_URL

print("=" * 80)
print("TESTING POSTGRESQL CONNECTION")
print("=" * 80)

print(f"\nDATABASE_URL: {DATABASE_URL}")

try:
    # Test connection
    print("\n1. Creating engine...")
    engine = create_engine(DATABASE_URL)
    
    print("2. Testing connection...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✅ PostgreSQL connected successfully!")
        print(f"   Version: {version[:80]}...")
        
        # Check if pgvector extension exists
        result = conn.execute(text("SELECT * FROM pg_extension WHERE extname='vector'"))
        if result.fetchone():
            print("✅ pgvector extension installed")
        else:
            print("⚠️  pgvector extension NOT found")
        
        # List all tables
        print("\n3. Checking tables...")
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
        else:
            print("⚠️  No tables found in public schema")
            
        # Check key tables
        print("\n4. Checking data in key tables...")
        
        if 'executions' in tables:
            result = conn.execute(text("SELECT COUNT(*) FROM executions"))
            exec_count = result.scalar()
            print(f"   - executions: {exec_count} rows")
            
            if exec_count > 0:
                # Check for Ragas scores
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(faithfulness) as with_faith,
                        COUNT(answer_relevancy) as with_relevancy
                    FROM executions
                """))
                row = result.fetchone()
                print(f"     → {row[1]} with faithfulness scores")
                print(f"     → {row[2]} with answer_relevancy scores")
                
                # Show last 5 executions
                result = conn.execute(text("""
                    SELECT 
                        e.id,
                        e.date_execution,
                        m.nom as model,
                        e.faithfulness,
                        e.answer_relevancy
                    FROM executions e
                    LEFT JOIN modeles m ON e.model_id = m.id
                    ORDER BY e.id DESC
                    LIMIT 5
                """))
                print("\n   Last 5 executions:")
                for row in result.fetchall():
                    print(f"     {row[0]:3d} | {row[1]} | {row[2]:20s} | F:{row[3]} AR:{row[4]}")
        else:
            print("   ⚠️  'executions' table not found")
            
        if 'scenarios' in tables:
            result = conn.execute(text("SELECT COUNT(*) FROM scenarios"))
            print(f"   - scenarios: {result.scalar()} rows")
        else:
            print("   ⚠️  'scenarios' table not found")
            
        if 'modeles' in tables:
            result = conn.execute(text("SELECT COUNT(*) FROM modeles"))
            print(f"   - modeles: {result.scalar()} rows")
        else:
            print("   ⚠️  'modeles' table not found")
            
        if 'utilisateurs' in tables:
            result = conn.execute(text("SELECT COUNT(*) FROM utilisateurs"))
            print(f"   - utilisateurs: {result.scalar()} rows")
        else:
            print("   ⚠️  'utilisateurs' table not found")
    
    print("\n" + "=" * 80)
    print("CONNECTION TEST COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPossible causes:")
    print("  1. PostgreSQL container not running")
    print("  2. Wrong credentials in .env")
    print("  3. Network/firewall blocking port 5432")
    print("\nCheck with: docker ps | grep postgres")
    sys.exit(1)
