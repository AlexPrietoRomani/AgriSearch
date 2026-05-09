"""
Archivo: project.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Definición de modelos relacionales (SQLAlchemy) para la persistencia de datos en
AgriSearch. Este esquema modela el dominio completo de la aplicación, desde la
gestión de proyectos aislados y el historial de búsquedas, hasta el seguimiento
detallado de artículos científicos, sesiones de cribado y decisiones de inclusión.

Acciones Principales:
    - Definición de tablas y relaciones para el motor SQLite.
    - Implementación de lógica de auditoría mediante marcas de tiempo UTC.
    - Soporte para rastreo de duplicados y estados de procesamiento de documentos.

Estructura Interna:
    - `Project`: Contenedor raíz de la investigación.
    - `Article`: Entidad central que representa un trabajo científico.
    - `SearchQuery`: Registro de ejecuciones de búsqueda.

Entradas / Dependencias:
    - `SQLAlchemy`: ORM para la gestión de la base de datos.
    - `app.db.database.Base`: Clase base declarativa.

Salidas / Efectos:
    - Define y estructura el esquema físico de la base de datos SQLite.
    - Gestiona la integridad referencial y las eliminaciones en cascada.

Ejemplo de Integración:
    from app.models.project import Project, Article
    project = Project(name="Agricultura de Precisión")
    article = Article(title="Detección de Plagas con CNN", project_id=project.id)
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
    """
    Genera una cadena de texto representando un UUID4 único.

    Returns:
        str: UUID único aleatorio.
    """
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """
    Retorna el objeto datetime actual con zona horaria UTC.

    Returns:
        datetime: Marca de tiempo actual en UTC.
    """
    return datetime.now(timezone.utc)


class AgriArea(str, PyEnum):
    """
    Categorías de áreas agrícolas para clasificar proyectos.
    """
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
    """
    Estados posibles de la descarga de un artículo científico.
    """
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PAYWALL = "paywall"
    NOT_FOUND = "not_found"
    MANUAL = "manual"


class ScreeningDecisionStatus(str, PyEnum):
    """
    Etiquetas de decisión para el proceso de cribado (alineadas con PRISMA).
    """
    PENDING = "pending"      # No revisado aún
    INCLUDE = "include"      # ✅ Relevante
    EXCLUDE = "exclude"      # ❌ No relevante (requiere motivo)
    MAYBE = "maybe"          # 🟡 Incierto, revisar después


class Project(Base):
    """
    Representa un proyecto de revisión sistemática. 
    Cada proyecto es un contenedor aislado para búsquedas y artículos.
    """

    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agri_area = Column(String(500), default="general")
    language = Column(String(10), default="es")  # Formato BCP-47
    llm_model = Column(String(100), nullable=True)  # Modelo LLM preferido
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relaciones
    articles = relationship("Article", back_populates="project", cascade="all, delete-orphan")
    search_queries = relationship("SearchQuery", back_populates="project", cascade="all, delete-orphan")
    screening_sessions = relationship("ScreeningSession", back_populates="project", cascade="all, delete-orphan")
    search_sessions = relationship("SearchSession", back_populates="project", cascade="all, delete-orphan")


class SearchQuery(Base):
    """
    Almacena una consulta de búsqueda ejecutada dentro de un proyecto.
    """

    __tablename__ = "search_queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    search_session_id = Column(String, ForeignKey("search_sessions.id"), nullable=True)
    raw_input = Column(Text, nullable=False)  # Entrada en lenguaje natural del usuario
    generated_query = Column(Text, nullable=False)  # Consulta booleana generada por LLM
    databases_used = Column(String(500), nullable=False)  # Bases de datos separadas por coma
    total_results = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    adapted_queries_json = Column(Text, nullable=True)  # Representación JSON de consultas adaptadas
    created_at = Column(DateTime, default=utcnow)

    # Relaciones
    project = relationship("Project", back_populates="search_queries")
    search_session = relationship("SearchSession", back_populates="search_queries")
    raw_results = relationship("SearchResultRaw", back_populates="search_query")


class Article(Base):
    """
    Representa un artículo científico identificado durante una búsqueda sistemática.
    """

    __tablename__ = "articles"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    search_query_id = Column(String, ForeignKey("search_queries.id"), nullable=True)

    # --- Metadatos bibliográficos ---
    doi = Column(String(255), nullable=True, index=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=True)  # Separados por comas
    year = Column(Integer, nullable=True)
    abstract = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=True)
    keywords = Column(Text, nullable=True)

    # --- Seguimiento de origen ---
    source_database = Column(String(100), nullable=False)  # openalex, semantic_scholar, arxiv, manual
    external_id = Column(String(500), nullable=True)  # ID en la base de datos original
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(String, nullable=True)

    # --- Estado de Descarga y Procesamiento ---
    download_status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    local_pdf_path = Column(String(1000), nullable=True)
    local_md_path = Column(String(1000), nullable=True)
    parsed_status = Column(String(20), default="pending")  # pending, success, failed
    
    # --- Tipo de Documento ---
    # Valores normalizados: journal-article | book | book-chapter | thesis | preprint | conference-paper | report | dataset | other
    document_type = Column(String(50), default="journal-article", nullable=True)
    
    # --- Enriquecimiento de Fase 2 ---
    llm_summary = Column(Text, nullable=True)
    relevance_score = Column(Float, default=0.0)
    methodology_type = Column(String(100), nullable=True)
    agri_variables_json = Column(Text, nullable=True)  # Variables extraídas por el LLM
    open_access_url = Column(String(1000), nullable=True)

    # --- Marcas de tiempo ---
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relaciones
    project = relationship("Project", back_populates="articles")
    screening_decisions = relationship("ScreeningDecision", back_populates="article", cascade="all, delete-orphan")


class ScreeningSession(Base):
    """
    Representa una sesión de cribado que agrupa decisiones sobre búsquedas seleccionadas.
    """

    __tablename__ = "screening_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # --- Identidad ---
    name = Column(String(255), nullable=True, default="Sesión de Screening")
    goal = Column(Text, nullable=True)  # Objetivo o meta de la sesión

    # --- Configuración ---
    search_query_ids = Column(Text, nullable=False)  # Array JSON de IDs de búsqueda seleccionados
    reading_language = Column(String(10), default="es")  # Idioma objetivo para traducción de abstracts
    translation_model = Column(String(100), default="gemma4:e4b")  # Modelo de Ollama para traducción
    total_articles = Column(Integer, default=0)  # Total de artículos en esta sesión

    # --- Progreso ---
    reviewed_count = Column(Integer, default=0)
    included_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    maybe_count = Column(Integer, default=0)

    # --- Marcas de tiempo ---
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relaciones
    project = relationship("Project", back_populates="screening_sessions")
    decisions = relationship("ScreeningDecision", back_populates="session", cascade="all, delete-orphan")


class ScreeningDecision(Base):
    """
    Registra una decisión individual de cribado para un artículo dentro de una sesión.
    """

    __tablename__ = "screening_decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("screening_sessions.id"), nullable=False)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False)

    # --- Decisión ---
    decision = Column(
        Enum(ScreeningDecisionStatus),
        default=ScreeningDecisionStatus.PENDING,
    )
    exclusion_reason = Column(String(255), nullable=True)  # Obligatorio si decision=exclude
    reviewer_note = Column(Text, nullable=True)  # Nota de texto libre opcional
    
    # --- Caché de abstract traducido ---
    translated_abstract = Column(Text, nullable=True)  # Traducción cacheada por LLM
    original_language = Column(String(10), nullable=True)  # Idioma detectado del abstract original

    # --- Ordenamiento ---
    display_order = Column(Integer, default=0)  # Orden en que se muestra el artículo

    # --- Marcas de tiempo ---
    decided_at = Column(DateTime, nullable=True)  # Momento en que se tomó la decisión
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relaciones
    session = relationship("ScreeningSession", back_populates="decisions")
    article = relationship("Article", back_populates="screening_decisions")


class SearchSession(Base):
    """
    Agrupa búsquedas dentro de una sesión de usuario.
    Permite rastrear el historial de búsquedas por proyecto.
    """

    __tablename__ = "search_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String(20), default="active")  # active, completed, aborted
    started_at = Column(DateTime, default=utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_searches = Column(Integer, default=0)
    user_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relaciones
    project = relationship("Project", back_populates="search_sessions")
    search_queries = relationship("SearchQuery", back_populates="search_session")


class SearchResultRaw(Base):
    """
    Almacena TODOS los DOIs encontrados en una búsqueda, incluyendo duplicados.
    Permite auditoría completa y trazabilidad de resultados por BD.
    """

    __tablename__ = "search_results_raw"

    id = Column(String, primary_key=True, default=generate_uuid)
    search_query_id = Column(String, ForeignKey("search_queries.id"), nullable=False)
    source_database = Column(String(100), nullable=False)
    doi = Column(String(255), nullable=True, index=True)
    title = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    was_duplicate = Column(Boolean, default=False)
    duplicate_reason = Column(String(50), nullable=True)  # doi_exact, title_fuzzy, project_doi, project_title
    matched_article_id = Column(String, ForeignKey("articles.id"), nullable=True)
    action = Column(String(20), default="stored")  # stored, skipped_duplicate, error
    created_at = Column(DateTime, default=utcnow)

    # Relaciones
    search_query = relationship("SearchQuery", back_populates="raw_results")
