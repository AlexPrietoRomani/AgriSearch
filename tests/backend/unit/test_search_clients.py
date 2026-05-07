"""
Archivo: test_search_clients.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas unitarias para el manejo de consultas en los clientes de búsqueda.
Verifica que los clientes MCP para ArXiv y otros motores formateen correctamente
las queries antes de enviarlas a sus respectivas APIs, evitando duplicidad de
prefijos y extrayendo conceptos clave para el motor de búsqueda.

Acciones Principales:
    - Validación de que ArXiv no duplique el prefijo 'all:' en consultas complejas.
    - Verificación de la adición automática del prefijo 'all:' en consultas de texto plano.
    - Prueba de la lógica de extracción de conceptos desde queries booleanas.
    - Validación de la eliminación de operadores lógicos (AND, OR, NOT) en la extracción de conceptos.

Entradas / Dependencias:
    - Mocks de `aiohttp.ClientSession` para evitar llamadas reales a red.
    - Funciones auxiliares de `search_service`.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_search_clients.py
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Agregar backend al path para resolver importaciones
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


# ── ArXiv Client Tests ──

class TestArxivClient:
    """Tests para el formateo de consultas en el cliente de ArXiv."""

    @pytest.mark.asyncio
    async def test_arxiv_no_duplicate_all_prefix(self):
        """
        Verifica que ArXiv NO añada un segundo prefijo 'all:' si ya existe uno.
        """
        from app.services.mcp_clients.arxiv_client import search_arxiv

        query_from_builder = 'all:"biological control" AND all:"thrips"'

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value='<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session

            await search_arxiv(query_from_builder, max_results=5)

            # Verificar que 'all:all:' no esté presente en la query enviada
            call_args = mock_session.get.call_args
            params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][1] if len(call_args[0]) > 1 else None
            
            if params:
                search_query = params.get("search_query", "")
                assert "all:all:" not in search_query, f"Doble prefijo detectado en: {search_query}"

    @pytest.mark.asyncio
    async def test_arxiv_adds_prefix_for_plain_text(self):
        """
        Verifica que ArXiv añada el prefijo 'all:' a consultas de texto plano.
        """
        from app.services.mcp_clients.arxiv_client import search_arxiv

        query_plain = "machine learning agriculture"

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value='<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)

            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = mock_session

            await search_arxiv(query_plain, max_results=5)

            call_args = mock_session.get.call_args
            params = call_args[1]["params"] if "params" in call_args[1] else None

            if params:
                search_query = params.get("search_query", "")
                assert search_query.startswith("all:"), f"Se esperaba el prefijo 'all:' en: {search_query}"


# ── Concept Extraction Tests ──

class TestConceptExtraction:
    """Tests para la extracción de conceptos clave desde strings de consulta."""

    def test_extract_from_boolean_query(self):
        """
        Verifica la extracción de conceptos desde una consulta de estilo booleano.
        """
        from app.services.search_service import _extract_concepts_from_query

        query = "biological control AND thrips AND strawberry"
        concepts = _extract_concepts_from_query(query)
        
        assert len(concepts) >= 3
        lower_concepts = [c.lower() for c in concepts]
        assert any("biological control" in c for c in lower_concepts)
        assert any("thrips" in c for c in lower_concepts)
        assert any("strawberry" in c for c in lower_concepts)

    def test_extract_from_plain_text(self):
        """
        Verifica la extracción de conceptos desde descripciones de texto plano.
        """
        from app.services.search_service import _extract_concepts_from_query

        query = "pest management soybean efficacy"
        concepts = _extract_concepts_from_query(query)
        assert len(concepts) > 0

    def test_extract_empty_query(self):
        """
        Verifica que una consulta vacía retorne una lista vacía.
        """
        from app.services.search_service import _extract_concepts_from_query

        assert _extract_concepts_from_query("") == []
        assert _extract_concepts_from_query("  ") == []

    def test_extract_removes_boolean_operators(self):
        """
        Verifica que los operadores booleanos sean eliminados de la lista de conceptos.
        """
        from app.services.search_service import _extract_concepts_from_query

        query = "(control OR management) AND (pest OR insect) NOT review"
        concepts = _extract_concepts_from_query(query)
        
        for concept in concepts:
            assert concept.upper() != "AND"
            assert concept.upper() != "OR"
            assert concept.upper() != "NOT"
