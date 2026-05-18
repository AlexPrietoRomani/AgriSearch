"""Script para crear la tabla article_references."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import engine, Base
from app.models import ArticleReference  # noqa: F401 - registra el modelo


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabla article_references creada exitosamente.")

    # Verificar con sqlite3 sync
    import sqlite3
    db_path = Path(__file__).parent / "data" / "agrisearch.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(article_references)")
    cols = cursor.fetchall()
    print(f"Columnas ({len(cols)}):")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
