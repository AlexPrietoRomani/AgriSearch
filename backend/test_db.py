import asyncio
import logging
from app.db.database import init_db
from app.models.project import Project, Article

logging.basicConfig(level=logging.DEBUG)

async def main():
    print("Initializing DB...")
    await init_db()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
