"""
AgriSearch Backend - FastAPI Application Entry Point.

Registers all routes, CORS, lifespan events, and the database.
"""

import logging
import sys
import asyncio
from contextlib import asynccontextmanager

# Fix for aiosqlite/SQLAlchemy async deadlocks on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.v1 import projects, search, screening, system

settings = get_settings()

# ── Logging ──
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🌱 AgriSearch v%s starting...", settings.app_version)
    # Database initialization is handled externally (via test_db.py/alembic) to avoid Windows deadlocks
    logger.info("✅ Server startup complete")
    yield
    logger.info("🛑 AgriSearch shutting down")


# ── App ──
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Plataforma de Búsqueda Sistemática y Asistente de Investigación Agrícola basada en PRISMA 2020",
    lifespan=lifespan,
)

# ── CORS ──
# En desarrollo permitimos todo para evitar bloqueos entre Astro y FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # settings.cors_origins (especificado en config.py) o "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Routes ──
app.include_router(system.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(screening.router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
