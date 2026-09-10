"""Restore database from SQL backup with error handling"""
import sqlite3
import re

# Read backup file
print("Reading backup file...")
with open('backups/ai_benchmark_backup_20260816_202022.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Connect to database
print("Connecting to database...")
conn = sqlite3.connect('data/ai_benchmark.db')
cursor = conn.cursor()

# Split into individual statements and execute
print("Executing SQL statements...")
statements = []
current_statement = []

for line in sql_content.split('\n'):
    # Skip comments
    if line.strip().startswith('--') or line.strip().startswith('/*'):
        continue
    
    current_statement.append(line)
    
    # If line ends with semicolon, it's the end of a statement
    if line.strip().endswith(';'):
        statement = '\n'.join(current_statement)
        if statement.strip():
            statements.append(statement)
        current_statement = []

print(f"Found {len(statements)} SQL statements")

# Execute statements one by one
success_count = 0
error_count = 0

for i, statement in enumerate(statements):
    try:
        cursor.execute(statement)
        success_count += 1
        if (i + 1) % 100 == 0:
            print(f"  Executed {i + 1}/{len(statements)} statements...")
    except sqlite3.Error as e:
        error_count += 1
        if error_count <= 5:  # Only show first 5 errors
            print(f"  Error in statement {i + 1}: {e}")
            if error_count == 5:
                print(f"  (suppressing further errors...)")

conn.commit()

# Verify restoration
print("\n=== VERIFICATION ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables found: {[t[0] for t in tables]}")

cursor.execute("SELECT COUNT(*) FROM executions")
exec_count = cursor.fetchone()[0]
print(f"Executions count: {exec_count}")

cursor.execute("SELECT COUNT(*) FROM executions WHERE faithfulness IS NOT NULL")
valid_count = cursor.fetchone()[0]
print(f"Executions with Ragas scores: {valid_count}")

conn.close()

print(f"\n✅ Restoration complete: {success_count} statements succeeded, {error_count} errors")
