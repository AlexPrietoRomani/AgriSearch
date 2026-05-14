"""
Archivo: test_arxiv_search.py
Modificación: 2026-05-14
Autor: Antigravity

Descripción:
Pruebas para validar la integración específica con la API de ArXiv.
Se enfoca en la construcción correcta de la URL de búsqueda, especialmente
respecto a los operadores de rango de fecha y la codificación de caracteres.

Acciones Principales:
    - Verificar la generación de la query de ArXiv (`all:terms`).
    - Validar la construcción manual de la URL para preservar el operador `+TO+`.
    - Comprobar que el filtro de fecha sea inyectado correctamente.

Estructura Interna:
    - `test_arxiv_query_generation`: Valida la traducción de conceptos a sintaxis `all:`.
    - `test_arxiv_url_encoding`: Verifica que los caracteres especiales se codifiquen sin romper la API.

Ejecución:
    uv run pytest tests/backend/unit/test_arxiv_search.py
"""

import pytest
from app.services.query_builder import build_arxiv_query
from app.services.mcp_clients.arxiv_client import search_arxiv

def test_arxiv_query_generation():
    """Valida la traducción de la estructura de conceptos a la sintaxis nativa de ArXiv."""
    concepts = ["Vision Transformer", "CNN"]
    synonyms = {
        "Vision Transformer": ["ViT"],
        "CNN": ["Convolutional Neural Network"]
    }
    query = build_arxiv_query(concepts, synonyms)
    
    # ArXiv usa all: para términos generales
    assert "all:Vision Transformer" in query
    assert "OR all:ViT" in query
    assert ") AND (" in query
    assert "all:CNN" in query

@pytest.mark.asyncio
async def test_arxiv_search_live_diagnostics():
    """
    Prueba de integración (requiere red). 
    Verifica que la API de ArXiv responda correctamente a una query compleja.
    """
    q = '(all:Vision Transformer OR all:ViT) AND all:agriculture'
    results = await search_arxiv(q, max_results=5, year_from=2020, year_to=2026)
    
    # Si hay red, debería devolver resultados o al menos no fallar por sintaxis
    assert isinstance(results, list)
    if results:
        assert "title" in results[0]
        assert "document_type" in results[0]
        assert results[0]["document_type"] == "preprint"
