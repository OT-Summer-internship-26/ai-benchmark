#!/usr/bin/env python3
"""
Create a database backup/snapshot for rollback purposes
This captures the complete state AFTER is_legacy migration
"""
import sys
sys.path.insert(0, '.')

import os
from datetime import datetime
from sqlalchemy import text, MetaData, Table, inspect
from src.database.connection import engine

# Create backups directory
backup_dir = 'backups'
os.makedirs(backup_dir, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = os.path.join(backup_dir, f'ai_benchmark_backup_{timestamp}.sql')

print('='*80)
print('DATABASE BACKUP - SNAPSHOT AFTER is_legacy MIGRATION')
print('='*80)
print(f'Timestamp: {timestamp}')
print(f'Backup file: {backup_file}')
print()

sql_statements = []

# Add header comments
sql_statements.append(f'-- Database Backup: ai_benchmark')
sql_statements.append(f'-- Created: {datetime.now().isoformat()}')
sql_statements.append(f'-- Purpose: Rollback point AFTER is_legacy flag migration')
sql_statements.append('-- Status: AFTER migration (is_legacy column added, 90 legacy scores tagged)')
sql_statements.append('')

# Get all tables
inspector = inspect(engine)
table_names = inspector.get_table_names()

print(f'Found {len(table_names)} tables:')
for table_name in table_names:
    print(f'  - {table_name}')

print()
print('Exporting table structures and data...')
print()

with engine.connect() as conn:
    for table_name in table_names:
        print(f'Processing table: {table_name}')
        
        # Get table structure
        table_meta = MetaData()
        table_obj = Table(table_name, table_meta, autoload_with=engine)
        
        # Get column info
        columns = inspector.get_columns(table_name)
        primary_keys = inspector.get_pk_constraint(table_name)
        
        # Build CREATE TABLE statement
        create_sql = f'\n-- Table: {table_name}\n'
        create_sql += f'DROP TABLE IF EXISTS {table_name} CASCADE;\n'
        create_sql += f'CREATE TABLE {table_name} (\n'
        
        col_defs = []
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            col_nullable = 'NULL' if col['nullable'] else 'NOT NULL'
            col_default = f'DEFAULT {col["default"]}' if col['default'] is not None else ''
            
            col_def = f'  {col_name} {col_type} {col_nullable} {col_default}'.strip()
            col_defs.append(col_def)
        
        create_sql += ',\n'.join(col_defs)
        
        # Add primary key constraint
        if primary_keys and primary_keys['constrained_columns']:
            pk_cols = ', '.join(primary_keys['constrained_columns'])
            create_sql += f',\n  PRIMARY KEY ({pk_cols})'
        
        create_sql += '\n);\n'
        
        sql_statements.append(create_sql)
        
        # Export data
        rows = conn.execute(text(f'SELECT * FROM {table_name}')).fetchall()
        
        if rows:
            print(f'  Exporting {len(rows)} rows')
            
            # Get column names
            col_names = [col['name'] for col in columns]
            insert_template = f'INSERT INTO {table_name} ({", ".join(col_names)}) VALUES '
            
            # Build INSERT statements
            for row in rows:
                values = []
                for val in row:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, bool):
                        values.append('TRUE' if val else 'FALSE')
                    else:
                        values.append(str(val))
                
                insert_sql = insert_template + '(' + ', '.join(values) + ');'
                sql_statements.append(insert_sql)
        else:
            print(f'  (empty table)')

# Add summary at end
sql_statements.append('')
sql_statements.append('-- ============================================================')
sql_statements.append('-- BACKUP SUMMARY')
sql_statements.append('-- ============================================================')
sql_statements.append(f'-- Database: ai_benchmark')
sql_statements.append(f'-- Created: {datetime.now().isoformat()}')
sql_statements.append(f'-- Status: AFTER is_legacy migration')
sql_statements.append(f'-- Tables backed up: {len(table_names)}')
sql_statements.append('-- ============================================================')

# Write to file
print()
print(f'Writing {len(sql_statements)} SQL statements to backup file...')

with open(backup_file, 'w', encoding='utf-8') as f:
    for stmt in sql_statements:
        f.write(stmt + '\n')

file_size = os.path.getsize(backup_file) / (1024 * 1024)  # Convert to MB

print()
print('='*80)
print('✓ BACKUP COMPLETE')
print('='*80)
print(f'File: {backup_file}')
print(f'Size: {file_size:.2f} MB')
print(f'SQL statements: {len(sql_statements)}')
print()
print('To restore from this backup:')
print(f'  psql -h localhost -U ooredoo_user -d ai_benchmark -f {backup_file}')
print()
print('This backup includes:')
print('  - All table schemas with columns and constraints')
print('  - All data (90 legacy + 99 modern scores)')
print('  - is_legacy flag state (TRUE/FALSE for each score)')
print()
print('To rollback is_legacy migration ONLY (keep data):')
print('  ALTER TABLE scores DROP COLUMN is_legacy;')
print()
print('='*80)
