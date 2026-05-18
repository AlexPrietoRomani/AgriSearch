"""
Archivo: main.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Punto de entrada principal para la aplicación FastAPI del backend de AgriSearch.
Se encarga de inicializar la base de datos, configurar los eventos del ciclo de vida,
las políticas de CORS y registrar todos los routers de la API.

Acciones Principales:
    - Inicializa la base de datos de manera asíncrona.
    - Configura el enrutador central integrando distintos módulos (projects, search, etc.).
    - Proporciona un endpoint de verificación de salud (health check).

Estructura Interna:
    - `lifespan`: Administra los eventos de arranque y apagado del servidor.
    - `health_check`: Proporciona la ruta /health para verificar el estado de la API.

Entradas / Dependencias:
    - Variables de entorno cargadas mediante `get_settings`.
    - Módulos internos de rutas y base de datos.

Salidas / Efectos:
    - Inicializa la instancia global de `FastAPI`.

Integración UI:
    - Este archivo es el servidor backend que expone los endpoints que serán consumidos por el frontend.
    - Es ejecutado generalmente mediante uvicorn (ej. `uvicorn app.main:app --reload`).
"""

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.v1 import projects, search, screening, system, events, graphs

# Parche para los deadlocks de aiosqlite/SQLAlchemy en Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestiona los eventos del ciclo de vida de la aplicación.
    
    Se encarga de inicializar la base de datos al arrancar el servidor
    y de manejar el apagado de forma segura.

    Args:
        app (FastAPI): La instancia de la aplicación FastAPI en ejecución.

    Yields:
        None: Suspende la ejecución para mantener el estado durante la vida del servidor.
    """
    logging.info("Starting up...")
    await init_db()
    yield
    logging.info("Shutting down...")

app = FastAPI(
    title="AgriSearch API",
    description="Backend for AgriSearch - AI-powered Agricultural Research Paper Search & Review.",
    version=settings.app_version,
    lifespan=lifespan,
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, se debe restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas ──
app.include_router(system.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(screening.router, prefix="/api/v1")
app.include_router(graphs.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Verifica el estado de salud de la API.

    Retorna información básica sobre la aplicación y su versión para comprobar 
    que el servidor está funcionando correctamente.

    Returns:
        Dict[str, Any]: Un diccionario con el estado, nombre y versión de la aplicación.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
