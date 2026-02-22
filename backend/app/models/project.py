"""
AgriSearch Backend - SQLAlchemy models for Projects and Articles.

All data is scoped by project_id to ensure isolation between reviews.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def generate_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class AgriArea(str, PyEnum):
    """Agricultural area categories."""
    GENERAL = "general"
    ENTOMOLOGY = "entomology"
    PHYTOPATHOLOGY = "phytopathology"
    BREEDING = "breeding"
    BIOTECHNOLOGY = "biotechnology"
    PRECISION_AGRICULTURE = "precision_agriculture"
    SOIL_SCIENCE = "soil_science"
    AGRONOMY = "agronomy"
    WEED_SCIENCE = "weed_science"
    OTHER = "other"


class DownloadStatus(str, PyEnum):
    """Article download status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PAYWALL = "paywall"
    NOT_FOUND = "not_found"
    MANUAL = "manual"


class Project(Base):
    """A systematic review project. Each project is fully isolated."""

    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agri_area = Column(Enum(AgriArea), default=AgriArea.GENERAL)
    language = Column(String(10), default="es")  # BCP-47
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    articles = relationship("Article", back_populates="project", cascade="all, delete-orphan")
    search_queries = relationship("SearchQuery", back_populates="project", cascade="all, delete-orphan")


class SearchQuery(Base):
    """A stored search query executed in a project."""

    __tablename__ = "search_queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    raw_input = Column(Text, nullable=False)  # User's natural language input
    generated_query = Column(Text, nullable=False)  # LLM-generated boolean query
    databases_used = Column(String(500), nullable=False)  # Comma-separated
    total_results = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    project = relationship("Project", back_populates="search_queries")


class Article(Base):
    """A scientific article identified during a systematic search."""

    __tablename__ = "articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    search_query_id = Column(String, ForeignKey("search_queries.id"), nullable=True)

    # --- Bibliographic metadata ---
    doi = Column(String(255), nullable=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)  # Comma-separated
    year = Column(Integer, nullable=True)
    abstract = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=True)
    keywords = Column(Text, nullable=True)

    # --- Source tracking ---
    source_database = Column(String(100), nullable=False)  # openalex, semantic_scholar, arxiv, manual
    external_id = Column(String(500), nullable=True)  # ID in the source database
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(String, nullable=True)

    # --- Download status ---
    download_status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    local_pdf_path = Column(String(1000), nullable=True)
    open_access_url = Column(String(1000), nullable=True)

    # --- Timestamps ---
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project = relationship("Project", back_populates="articles")
