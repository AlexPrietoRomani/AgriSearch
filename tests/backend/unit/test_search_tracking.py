"""
Archivo: test_search_tracking.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas de integración para el sistema de trazabilidad de búsquedas. 
Valida la persistencia y relación entre las nuevas entidades de auditoría: 
`SearchSession` y `SearchResultRaw`, asegurando que se capturen correctamente 
todos los resultados (incluyendo duplicados) para mantener la transparencia 
en el proceso de búsqueda federada.

Acciones Principales:
    - Verificación de creación de sesiones de búsqueda vinculadas a proyectos.
    - Validación del registro de resultados crudos (Raw Results).
    - Comprobación del rastreo de duplicados y motivos de duplicidad.
    - Validación de relaciones ORM entre Proyectos, Consultas y Resultados.
    - Prueba de integridad referencial con artículos existentes.

Estructura Interna:
    - `TestSearchSessionModel`: Pruebas de la entidad de sesión.
    - `TestSearchResultRawModel`: Pruebas de la entidad de resultados de auditoría.

Entradas / Dependencias:
    - `app.models.project`.
    - `sqlalchemy.ext.asyncio`.
    - `pytest`.

Salidas / Efectos:
    - Valida la integridad del esquema en una base de datos SQLite en memoria.
    - No produce cambios persistentes en el disco.

Ejecución:
    pytest tests/backend/unit/test_search_tracking.py
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.project import (
    Base, Project, SearchQuery, Article, SearchSession, SearchResultRaw,
    generate_uuid, utcnow
)


@pytest.fixture
async def db_engine():
    """Motor de DB en memoria para tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Sesión transaccional para tests."""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
        await session.rollback()


class TestSearchSessionModel:
    """Tests del modelo SearchSession."""

    @pytest.mark.asyncio
    async def test_create_search_session(self, db_session):
        """Se puede crear un SearchSession."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        session = SearchSession(project_id=project.id)
        db_session.add(session)
        await db_session.flush()

        assert session.id is not None
        assert session.project_id == project.id
        assert session.status == "active"
        assert session.total_searches == 0

    @pytest.mark.asyncio
    async def test_search_session_belongs_to_project(self, db_session):
        """SearchSession tiene relación con Project."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        session = SearchSession(project_id=project.id)
        db_session.add(session)
        await db_session.flush()

        # Verificar que el proyecto tiene la sesión
        await db_session.refresh(project, ["search_sessions"])
        assert len(project.search_sessions) == 1
        assert project.search_sessions[0].id == session.id


class TestSearchResultRawModel:
    """Tests del modelo SearchResultRaw."""

    @pytest.mark.asyncio
    async def test_create_raw_result(self, db_session):
        """Se puede crear un SearchResultRaw."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        query = SearchQuery(
            project_id=project.id,
            raw_input="test query",
            generated_query="test AND query",
            databases_used="openalex",
        )
        db_session.add(query)
        await db_session.flush()

        raw = SearchResultRaw(
            search_query_id=query.id,
            source_database="openalex",
            doi="10.1234/test",
            title="Test Article",
            was_duplicate=False,
            action="stored",
        )
        db_session.add(raw)
        await db_session.flush()

        assert raw.id is not None
        assert raw.search_query_id == query.id
        assert raw.doi == "10.1234/test"
        assert raw.was_duplicate is False

    @pytest.mark.asyncio
    async def test_raw_result_duplicate_tracking(self, db_session):
        """Se puede marcar un resultado como duplicado."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        query = SearchQuery(
            project_id=project.id,
            raw_input="test query",
            generated_query="test AND query",
            databases_used="openalex",
        )
        db_session.add(query)
        await db_session.flush()

        raw = SearchResultRaw(
            search_query_id=query.id,
            source_database="openalex",
            doi="10.1234/duplicate",
            title="Duplicate Article",
            was_duplicate=True,
            duplicate_reason="doi_exact",
            action="skipped_duplicate",
        )
        db_session.add(raw)
        await db_session.flush()

        assert raw.was_duplicate is True
        assert raw.duplicate_reason == "doi_exact"
        assert raw.action == "skipped_duplicate"

    @pytest.mark.asyncio
    async def test_raw_result_belongs_to_query(self, db_session):
        """SearchResultRaw tiene relación con SearchQuery."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        query = SearchQuery(
            project_id=project.id,
            raw_input="test query",
            generated_query="test AND query",
            databases_used="openalex",
        )
        db_session.add(query)
        await db_session.flush()

        raw = SearchResultRaw(
            search_query_id=query.id,
            source_database="openalex",
            doi="10.1234/test",
            action="stored",
        )
        db_session.add(raw)
        await db_session.flush()

        await db_session.refresh(query, ["raw_results"])
        assert len(query.raw_results) == 1
        assert query.raw_results[0].doi == "10.1234/test"

    @pytest.mark.asyncio
    async def test_multiple_raw_results_per_query(self, db_session):
        """Una búsqueda puede tener múltiples resultados raw."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        query = SearchQuery(
            project_id=project.id,
            raw_input="test query",
            generated_query="test AND query",
            databases_used="openalex,crossref",
        )
        db_session.add(query)
        await db_session.flush()

        for i in range(5):
            raw = SearchResultRaw(
                search_query_id=query.id,
                source_database="openalex" if i % 2 == 0 else "crossref",
                doi=f"10.1234/test{i}",
                title=f"Article {i}",
                was_duplicate=(i % 3 == 0),
                action="stored" if i % 3 != 0 else "skipped_duplicate",
            )
            db_session.add(raw)
        await db_session.flush()

        await db_session.refresh(query, ["raw_results"])
        assert len(query.raw_results) == 5

    @pytest.mark.asyncio
    async def test_raw_result_with_matched_article(self, db_session):
        """SearchResultRaw puede referenciar un artículo matcheado."""
        project = Project(name="Test Project")
        db_session.add(project)
        await db_session.flush()

        query = SearchQuery(
            project_id=project.id,
            raw_input="test query",
            generated_query="test AND query",
            databases_used="openalex",
        )
        db_session.add(query)
        await db_session.flush()

        article = Article(
            project_id=project.id,
            title="Existing Article",
            source_database="openalex",
        )
        db_session.add(article)
        await db_session.flush()

        raw = SearchResultRaw(
            search_query_id=query.id,
            source_database="crossref",
            doi="10.1234/test",
            title="Duplicate of Existing",
            was_duplicate=True,
            duplicate_reason="doi_exact",
            matched_article_id=article.id,
            action="skipped_duplicate",
        )
        db_session.add(raw)
        await db_session.flush()

        assert raw.matched_article_id == article.id
