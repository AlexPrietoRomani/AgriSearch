"""
AgriSearch Backend - SQLAlchemy models for Projects, Articles, and Screening.

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


class ScreeningDecisionStatus(str, PyEnum):
    """Screening decision labels (PRISMA-aligned)."""
    PENDING = "pending"      # Not yet reviewed
    INCLUDE = "include"      # ✅ Relevant
    EXCLUDE = "exclude"      # ❌ Not relevant (requires reason)
    MAYBE = "maybe"          # 🟡 Uncertain, review later


class Project(Base):
    """A systematic review project. Each project is fully isolated."""

    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agri_area = Column(String(500), default="general")
    language = Column(String(10), default="es")  # BCP-47
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    articles = relationship("Article", back_populates="project", cascade="all, delete-orphan")
    search_queries = relationship("SearchQuery", back_populates="project", cascade="all, delete-orphan")
    screening_sessions = relationship("ScreeningSession", back_populates="project", cascade="all, delete-orphan")


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
    screening_decisions = relationship("ScreeningDecision", back_populates="article", cascade="all, delete-orphan")


class ScreeningSession(Base):
    """A screening session grouping decisions across selected searches."""

    __tablename__ = "screening_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # --- Identity ---
    name = Column(String(255), nullable=True, default="Sesión de Screening")  # Descriptive name
    goal = Column(Text, nullable=True)  # Session objective / goal

    # --- Configuration ---
    search_query_ids = Column(Text, nullable=False)  # JSON array of selected search query IDs
    reading_language = Column(String(10), default="es")  # Target language for abstract translation
    translation_model = Column(String(100), default="aya-expanse")  # Ollama model for translation
    total_articles = Column(Integer, default=0)  # Total articles in this session

    # --- Progress ---
    reviewed_count = Column(Integer, default=0)
    included_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    maybe_count = Column(Integer, default=0)

    # --- Timestamps ---
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    project = relationship("Project", back_populates="screening_sessions")
    decisions = relationship("ScreeningDecision", back_populates="session", cascade="all, delete-orphan")


class ScreeningDecision(Base):
    """A single screening decision for an article within a session."""

    __tablename__ = "screening_decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("screening_sessions.id"), nullable=False)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False)

    # --- Decision ---
    decision = Column(
        Enum(ScreeningDecisionStatus),
        default=ScreeningDecisionStatus.PENDING,
    )
    exclusion_reason = Column(String(255), nullable=True)  # Required when decision=exclude
    reviewer_note = Column(Text, nullable=True)  # Optional free-text note

    # --- Translated abstract cache ---
    translated_abstract = Column(Text, nullable=True)  # Cached LLM translation
    original_language = Column(String(10), nullable=True)  # Detected language of original abstract

    # --- Ordering ---
    display_order = Column(Integer, default=0)  # Order in which article is shown

    # --- Timestamps ---
    decided_at = Column(DateTime, nullable=True)  # When the decision was made
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    session = relationship("ScreeningSession", back_populates="decisions")
    article = relationship("Article", back_populates="screening_decisions")
