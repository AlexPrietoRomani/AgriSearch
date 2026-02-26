"""Quick script to create/update database tables."""
import asyncio
import sys
sys.path.insert(0, ".")
from app.models.project import Base, Project, SearchQuery, Article, ScreeningSession, ScreeningDecision
from app.db.database import init_db

async def main():
    await init_db()
    print("✅ Tables created/updated!")

if __name__ == "__main__":
    asyncio.run(main())
