import asyncio
import os
import sys

# Add current directory to path to find app module
sys.path.append(os.getcwd())

from app.db.database import engine
from app.models.project import Base

async def init_db():
    print(f"Initializing database at {engine.url}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
