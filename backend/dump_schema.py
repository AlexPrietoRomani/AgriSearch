import sqlite3
import json

con = sqlite3.connect('agrisearch.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row['name'] for row in cur.fetchall()]

schema = {}
for table in tables:
    cur.execute(f"PRAGMA table_info({table})")
    columns = [dict(row) for row in cur.fetchall()]
    
    cur.execute(f"SELECT * FROM {table} LIMIT 1")
    row = cur.fetchone()
    example = dict(row) if row else {}
    
    schema[table] = {
        'columns': columns,
        'example_row': example
    }

with open('../docs/database_schema_current.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print("Schema written to docs/database_schema_current.json")
