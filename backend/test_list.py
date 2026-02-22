import asyncio
from app.api.v1.projects import list_projects
from app.db.database import async_session_factory

async def main():
    print("Listing projects...")
    async with async_session_factory() as session:
        result = await list_projects(db=session)
        print("Got projects:", result)

if __name__ == "__main__":
    asyncio.run(main())
