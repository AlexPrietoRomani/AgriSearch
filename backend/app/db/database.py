"""
Archivo: database.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Motor de base de datos y gestión de sesiones para el backend de AgriSearch.
Utiliza SQLAlchemy asíncrono con aiosqlite para conectarse a una base de datos local SQLite.

Acciones Principales:
    - Inicializa el motor de base de datos asíncrono.
    - Gestiona la creación de sesiones para las consultas (dependency injection).
    - Crea las tablas de la base de datos al inicio.

Estructura Interna:
    - `Base`: Clase base declarativa para todos los modelos SQLAlchemy.
    - `get_db`: Generador asíncrono que proporciona sesiones de base de datos.
    - `init_db`: Función que crea todas las tablas en el inicio.

Entradas / Dependencias:
    - Configuración del entorno a través de `get_settings` (`database_url`).
    - Modelos de SQLAlchemy que heredan de `Base`.

Salidas / Efectos:
    - Modifica y lee el archivo `agrisearch.db`.
    - Proporciona instancias `AsyncSession` listas para usarse en los endpoints.

Ejemplo de Integración:
    from app.db.database import get_db, init_db
    
    # En FastAPI endpoints:
    @app.get("/items")
    async def read_items(db: AsyncSession = Depends(get_db)):
        ...
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()
print(f"DEBUG: Using database URL: {settings.database_url}")
print(f"DEBUG: Current CWD: {os.getcwd()}")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos SQLAlchemy.
    
    Todas las tablas de la base de datos deben heredar de esta clase para ser
    registradas en el motor de SQLAlchemy y creadas automáticamente por `init_db()`.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Proporciona una sesión de base de datos asíncrona.
    
    Esta función está diseñada para usarse como una dependencia en FastAPI.
    Garantiza que las transacciones se confirmen (commit) si no hay errores,
    o se reviertan (rollback) en caso de excepción, y siempre cierra la sesión al finalizar.

    Yields:
        AsyncSession: Una sesión activa de base de datos.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Crea todas las tablas en la base de datos al inicio de la aplicación.
    
    Sincroniza los metadatos de la clase `Base` con el esquema de la base de datos.
    Solo crea las tablas que aún no existen.

    Returns:
        None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
