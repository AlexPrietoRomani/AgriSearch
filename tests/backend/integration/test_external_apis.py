"""
Archivo: test_external_apis.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas de integración para validar la conectividad en vivo con APIs científicas externas.
Verifica que los clientes MCP para OpenAlex, Semantic Scholar y ArXiv puedan realizar
consultas, recibir respuestas y parsear los resultados correctamente.

Acciones Principales:
    - Validación de conectividad y respuesta de OpenAlex.
    - Validación de conectividad y respuesta de Semantic Scholar.
    - Validación de conectividad y respuesta de ArXiv (con manejo de rate limiting).
    - Verificación del funcionamiento de filtros por fecha (año) en las consultas.

Entradas / Dependencias:
    - Clientes MCP de búsqueda.
    - Conexión a Internet activa.

Ejemplo de Ejecución:
    pytest tests/backend/integration/test_external_apis.py
"""

import pytest
from app.services.mcp_clients.openalex_client import search_openalex
from app.services.mcp_clients.semantic_scholar_client import search_semantic_scholar
from app.services.mcp_clients.arxiv_client import search_arxiv


@pytest.mark.asyncio
async def test_openalex_connectivity():
    """
    Verifica que OpenAlex retorne resultados para un término común.
    """
    results = await search_openalex(query="Tomato", max_results=5)
    assert len(results) > 0
    assert "title" in results[0]
    assert results[0]["title"] is not None


@pytest.mark.asyncio
async def test_semantic_scholar_connectivity():
    """
    Verifica que Semantic Scholar retorne resultados para un término común.
    """
    results = await search_semantic_scholar(query="CNN", max_results=5)
    assert len(results) > 0
    assert "title" in results[0]


@pytest.mark.asyncio
async def test_arxiv_connectivity():
    """
    Verifica que ArXiv retorne resultados para un término común.

    Maneja con flexibilidad los casos de limitación de tasa (rate limiting).
    """
    results = await search_arxiv(query="Machine Learning", max_results=5)
    if results:
        assert len(results) > 0
        assert "title" in results[0]
    else:
        pytest.skip("ArXiv retornó 0 resultados (posible limitación de tasa)")


@pytest.mark.asyncio
async def test_openalex_date_filter():
    """
    Verifica que OpenAlex aplique correctamente los filtros de año.
    """
    results = await search_openalex(query="RAG", max_results=3, year_from=2023, year_to=2024)
    for r in results:
        if r.get("year"):
            assert 2023 <= int(r["year"]) <= 2024
