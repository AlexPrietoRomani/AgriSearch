"""
AgriSearch Backend - FastAPI Application Entry Point.

Registers all routes, CORS, lifespan events, and the database.
"""

import logging
import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.v1 import projects, search, screening, system, events

# Fix for aiosqlite/SQLAlchemy async deadlocks on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events - Initialize DB."""
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──
app.include_router(system.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
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
