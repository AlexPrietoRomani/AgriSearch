"""
Archivo: test_search_preview_api.py
Modificación: 2026-05-14
Autor: Antigravity

Descripción:
Prueba de integración para el endpoint de previsualización de queries.
Verifica que la API REST responda correctamente al payload de la query booleana
y devuelva el mapa de queries adaptadas esperado por el frontend.

Acciones Principales:
    - Enviar peticiones POST a /api/v1/search/preview-queries.
    - Validar que el esquema de respuesta contenga 'adapted_queries'.
    - Verificar que los formatos de query para cada BD sigan las reglas de negocio.

Ejecución:
    uv run pytest tests/backend/integration/test_search_preview_api.py
"""

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_preview_queries_endpoint():
    """Valida el flujo completo desde el endpoint hasta la generación de queries adaptadas."""
    payload = {
        "boolean_query": "(Vision Transformer OR ViT) AND (agriculture)",
        "databases": ["openalex", "arxiv", "semantic_scholar"]
    }
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/search/preview-queries", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "adapted_queries" in data
    adapted = data["adapted_queries"]
    
    # Verificaciones de formato por BD
    assert "openalex" in adapted
    assert "Vision Transformer ViT agriculture" in adapted["openalex"]
    
    assert "arxiv" in adapted
    assert "all:Vision Transformer" in adapted["arxiv"]
    assert "all:ViT" in adapted["arxiv"]
    
    assert "semantic_scholar" in adapted
    assert "Vision Transformer agriculture" in adapted["semantic_scholar"]

@pytest.mark.asyncio
async def test_preview_queries_empty_payload():
    """Verifica que el endpoint maneje correctamente payloads vacíos o incompletos."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Sin databases
        resp1 = await ac.post("/api/v1/search/preview-queries", json={"boolean_query": "test"})
        assert resp1.status_code == 200
        assert resp1.json()["adapted_queries"] == {}
        
        # Sin query
        resp2 = await ac.post("/api/v1/search/preview-queries", json={"databases": ["arxiv"]})
        assert resp2.status_code == 200
        assert resp2.json()["adapted_queries"] == {}
