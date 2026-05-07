"""
Archivo: conftest.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Configuración global y fixtures de pytest para las pruebas del backend de AgriSearch.
Define el ciclo de vida de la base de datos de pruebas (in-memory) y el event loop asíncrono.

Acciones Principales:
    - Inyección del path del backend en sys.path para importaciones locales.
    - Configuración del motor de base de datos asíncrono (SQLite in-memory).
    - Gestión de sesiones transaccionales para pruebas unitarias e integración.

Entradas / Dependencias:
    - SQLAlchemy (create_async_engine, AsyncSession).
    - Modelos de la aplicación (Base).
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import sys
from pathlib import Path

# Agregar el directorio backend al path para resolver importaciones de 'app'
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.models.project import Base
from app.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """
    Crea una instancia del bucle de eventos predeterminado para cada sesión de prueba.

    Yields:
        asyncio.AbstractEventLoop: El bucle de eventos asíncrono.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """
    Motor de base de datos temporal para pruebas.

    Utiliza SQLite in-memory y sincroniza el esquema de modelos definido en Base.

    Yields:
        AsyncEngine: Motor de SQLAlchemy configurado para pruebas.
    """
    # Usar una base de datos temporal en memoria para aislamiento total
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_db_url)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """
    Proporciona una sesión de base de datos transaccional para cada prueba.

    Realiza un rollback automático al finalizar la prueba para mantener la integridad.

    Args:
        db_engine: Fixture del motor de base de datos.

    Yields:
        AsyncSession: Sesión de base de datos asíncrona lista para usar.
    """
    async_session = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        yield session
        await session.rollback()
