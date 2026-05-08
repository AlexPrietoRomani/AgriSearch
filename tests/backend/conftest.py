"""
Archivo: conftest.py
Modificación: 2026-05-08
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

Salidas / Efectos:
    - Inyecta fixtures compartidos (`db_session`, `db_engine`, `sample_raw_articles`) en todos los tests.
    - Asegura un entorno de ejecución asíncrono aislado y predecible.
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


# ── Fixtures compartidos para tests del pipeline de búsqueda ──


@pytest.fixture
def sample_raw_articles():
    """
    Proporciona una muestra de artículos raw como los devuelven los MCP clients.
    Cada diccionario simula el formato estándar de respuesta de un cliente de BD.
    """
    return [
        {
            "doi": "10.1234/test.1",
            "title": "Remote Sensing for Crop Health",
            "authors": "Garcia, M.; Lopez, J.",
            "year": 2023,
            "abstract": "This study uses NDVI to assess crop health.",
            "journal": "Remote Sensing Journal",
            "url": "https://doi.org/10.1234/test.1",
            "keywords": "NDVI, remote sensing, agriculture",
            "source_database": "semantic_scholar",
            "open_access_url": "https://pdf.example.com/test1.pdf",
        },
        {
            "doi": "10.1234/test.2",
            "title": "Drone-Based Multispectral Imaging for Precision Agriculture",
            "authors": "Smith, A.; Johnson, B.",
            "year": 2022,
            "abstract": "UAV multispectral imaging for crop monitoring.",
            "journal": "Precision Agriculture",
            "url": "https://doi.org/10.1234/test.2",
            "keywords": "UAV, multispectral, precision agriculture",
            "source_database": "openalex",
            "open_access_url": None,
        },
        {
            "doi": "10.1234/test.1",  # Duplicate DOI — should be deduplicated
            "title": "Remote Sensing for Crop Health (Duplicate)",
            "authors": "Garcia, M.; Lopez, J.",
            "year": 2023,
            "abstract": "Duplicate entry from another DB.",
            "journal": "Remote Sensing Journal",
            "url": "https://doi.org/10.1234/test.1",
            "keywords": "NDVI",
            "source_database": "crossref",
            "open_access_url": None,
        },
        {
            "doi": None,
            "title": "Agricultural IoT Systems",
            "authors": "Lee, K.",
            "year": 2021,
            "abstract": "IoT in agriculture.",
            "journal": None,
            "url": None,
            "keywords": "IoT, agriculture",
            "source_database": "arxiv",
            "open_access_url": "https://arxiv.org/pdf/2101.00001.pdf",
        },
    ]


@pytest.fixture
def mock_llm_response():
    """
    Proporciona una respuesta simulada del LLM para el endpoint build-query.
    """
    return {
        "concepts": ["remote sensing", "crop health", "NDVI"],
        "synonyms": {
            "remote sensing": ["satellite imagery", "teledetección"],
            "crop health": ["plant health", "vegetation vigor"],
            "NDVI": ["Normalized Difference Vegetation Index"],
        },
        "boolean_query": "remote sensing AND crop health AND NDVI",
        "suggested_terms": ["AGROVOC:remote sensing", "MeSH:NDVI"],
        "pico_breakdown": {
            "P": "Crop plants",
            "I": "Remote sensing technology",
            "C": "Traditional monitoring",
            "O": "Health assessment accuracy",
        },
        "explanation": "Query generated for agricultural remote sensing research.",
    }


@pytest.fixture
def sample_openalex_work():
    """Proporciona un work raw de OpenAlex para tests de parsing."""
    return {
        "id": "https://openalex.org/W123456789",
        "doi": "https://doi.org/10.1234/test.oa",
        "title": "Satellite-Based Vegetation Index Analysis",
        "authorships": [
            {"author": {"display_name": "Maria Garcia"}},
            {"author": {"display_name": "Juan Lopez"}},
        ],
        "publication_year": 2023,
        "primary_location": {
            "source": {"display_name": "Remote Sensing of Environment"}
        },
        "keywords": [
            {"display_name": "NDVI"},
            {"display_name": "remote sensing"},
        ],
        "abstract_inverted_index": {
            "This": [0],
            "study": [1],
            "analyzes": [2],
            "NDVI": [3],
            "patterns": [4],
        },
        "best_oa_location": {
            "pdf_url": "https://example.com/paper.pdf",
            "landing_page_url": "https://example.com/paper",
        },
    }


@pytest.fixture
def sample_crossref_work():
    """Proporciona un work raw de CrossRef para tests de parsing."""
    return {
        "DOI": "10.1234/test.cr",
        "title": ["Crop Disease Detection with Deep Learning"],
        "author": [
            {"given": "Ana", "family": "Martinez"},
            {"given": "Pedro", "family": "Sanchez"},
        ],
        "published-print": {"date-parts": [[2022]]},
        "abstract": "<p>Abstract with <b>HTML</b> tags.</p>",
        "container-title": ["Journal of Agricultural Science"],
        "subject": ["agriculture", "deep learning", "crop disease"],
    }


@pytest.fixture
def sample_arxiv_xml():
    """Proporciona XML raw de ArXiv para tests de parsing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2301.12345v1</id>
            <title>Hyperspectral Imaging for Plant Stress Detection</title>
            <summary>A study on hyperspectral imaging for detecting plant stress.</summary>
            <published>2023-01-15T00:00:00Z</published>
            <author><name>Carlos Rodriguez</name></author>
            <author><name>Maria Fernandez</name></author>
            <category term="cs.CV"/>
            <category term="eess.IV"/>
            <link title="pdf" type="application/pdf" href="http://arxiv.org/pdf/2301.12345v1"/>
        </entry>
    </feed>"""


@pytest.fixture
def sample_scielo_item():
    """Proporciona un item raw de SciELO para tests de parsing."""
    return {
        "doi": "10.1590/test.scielo",
        "ti_es": ["Detección de enfermedades en cultivos con imágenes multiespectrales"],
        "ti_en": ["Crop Disease Detection with Multispectral Images"],
        "ab_es": ["Estudio sobre detección de enfermedades en cultivos tropicales."],
        "ab_en": ["Study on crop disease detection in tropical crops."],
        "au": ["Garcia, M.", "Lopez, J.", "Martinez, A."],
        "da": "2023-05-15",
        "ta": ["Tropical Plant Pathology"],
        "ur": ["https://www.scielo.br/j/tpp/a/test"],
        "kw": ["crop disease", "multispectral", "tropical agriculture"],
        "fulltext_pdf": "https://www.scielo.br/j/tpp/a/test.pdf",
    }


@pytest.fixture
def sample_oai_record():
    """Proporciona un registro Dublin Core de OAI-PMH para tests de parsing."""
    return {
        "title": ["Agri-Environmental Policy Analysis"],
        "creator": ["John Farmer", "Jane Researcher"],
        "date": ["2022-06"],
        "description": ["Analysis of agri-environmental policies in the EU."],
        "subject": ["agricultural policy", "environmental economics", "EU"],
        "identifier": [
            "https://doi.org/10.5555/oai.test",
            "http://ageconsearch.umn.edu/record/12345",
        ],
    }
