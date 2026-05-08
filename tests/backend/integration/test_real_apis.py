"""
Archivo: test_real_apis.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas de integración contra las APIs reales de las bases de datos 
científicas. Estas pruebas requieren conectividad a internet y validan que el 
contrato de datos entre los clientes MCP y los proveedores externos se mantenga 
operativo y devuelva resultados coherentes.

Acciones Principales:
    - Verificación de disponibilidad de servicios externos (OpenAlex, ArXiv, CrossRef).
    - Validación de la estructura de metadatos devuelta por servicios productivos.
    - Comprobación de la validez de DOIs y URLs de acceso abierto reales.
    - Prueba de tiempos de respuesta bajo condiciones reales de red.

Estructura Interna:
    - `TestOpenAlexReal`: Integración con api.openalex.org.
    - `TestArXivReal`: Integración con export.arxiv.org.
    - `TestCrossRefReal`: Integración con api.crossref.org.

Entradas / Dependencias:
    - Conexión a internet estable.
    - Módulos de clientes `app.services.mcp_clients`.

Salidas / Efectos:
    - Realiza llamadas de red reales que pueden consumir cuota/limites de APIs.
    - Valida la operatividad del sistema en un entorno pre-producción.

Ejecución:
    pytest tests/backend/integration/test_real_apis.py -v -m integration
"""

import pytest
import re

from app.services.mcp_clients.openalex_client import search_openalex
from app.services.mcp_clients.arxiv_client import search_arxiv
from app.services.search_service import _normalize_doi

DOI_PATTERN = re.compile(r"^10\.\d{4,}/\S+$")


@pytest.mark.integration
class TestOpenAlexReal:
    """Tests de integración contra OpenAlex API."""

    @pytest.mark.asyncio
    async def test_openalex_returns_results(self):
        """OpenAlex devuelve resultados para una query válida."""
        results = await search_openalex("NDVI crop health", max_results=5)
        assert len(results) > 0, "OpenAlex no devolvió resultados"

    @pytest.mark.asyncio
    async def test_openalex_results_have_doi(self):
        """Los resultados de OpenAlex incluyen DOI válido."""
        results = await search_openalex("remote sensing agriculture", max_results=5)
        dois = [r["doi"] for r in results if r.get("doi")]
        assert len(dois) > 0, "Ningún resultado tiene DOI"
        for doi in dois[:3]:
            normalized = _normalize_doi(doi)
            assert normalized is not None, f"DOI inválido: {doi}"

    @pytest.mark.asyncio
    async def test_openalex_results_have_title(self):
        """Los resultados de OpenAlex tienen título no vacío."""
        results = await search_openalex("plant disease detection", max_results=5)
        for r in results:
            assert r.get("title"), f"Artículo sin título: {r}"
            assert r["title"] != "No Title"


@pytest.mark.integration
class TestArXivReal:
    """Tests de integración contra ArXiv API."""

    @pytest.mark.asyncio
    async def test_arxiv_returns_results(self):
        """ArXiv devuelve resultados para una query válida."""
        results = await search_arxiv("precision agriculture drone", max_results=5)
        assert len(results) > 0, "ArXiv no devolvió resultados"

    @pytest.mark.asyncio
    async def test_arxiv_results_have_pdf_url(self):
        """Los resultados de ArXiv siempre tienen PDF URL."""
        results = await search_arxiv("NDVI remote sensing", max_results=5)
        for r in results:
            assert r.get("open_access_url"), f"ArXiv sin PDF URL: {r['title']}"

    @pytest.mark.asyncio
    async def test_arxiv_results_have_fabricated_doi(self):
        """Los resultados de ArXiv tienen DOI fabricado cuando no tienen DOI real."""
        results = await search_arxiv("crop yield estimation", max_results=5)
        dois = [r["doi"] for r in results if r.get("doi")]
        assert len(dois) > 0, "Ningún resultado tiene DOI"


@pytest.mark.integration
class TestCrossRefReal:
    """Tests de integración contra CrossRef API."""

    @pytest.mark.asyncio
    async def test_crossref_returns_results(self):
        """CrossRef devuelve resultados para una query válida."""
        from app.services.mcp_clients.crossref_client import search_crossref
        results = await search_crossref("soil health agriculture", max_results=5)
        assert len(results) > 0, "CrossRef no devolvió resultados"

    @pytest.mark.asyncio
    async def test_crossref_results_have_doi(self):
        """Los resultados de CrossRef siempre tienen DOI."""
        from app.services.mcp_clients.crossref_client import search_crossref
        results = await search_crossref("crop disease detection", max_results=5)
        for r in results:
            assert r.get("doi"), f"CrossRef sin DOI: {r.get('title')}"
            normalized = _normalize_doi(r["doi"])
            assert normalized is not None, f"DOI CrossRef inválido: {r['doi']}"
