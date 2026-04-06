import asyncio
import os
import sys
from sqlalchemy import select

# Add current directory to path
sys.path.append(os.getcwd())

from app.models.project import Article
from app.db.database import engine

async def check_db():
    async with engine.connect() as conn:
        # Check tables
        from sqlalchemy import inspect
        def get_columns(target_conn):
            inspector = inspect(target_conn)
            return {table: [col['name'] for col in inspector.get_columns(table)] for table in inspector.get_table_names()}
        
        tables = await conn.run_sync(get_columns)
        for table, cols in tables.items():
            print(f"Table {table}: {cols}")

if __name__ == "__main__":
    asyncio.run(check_db())
