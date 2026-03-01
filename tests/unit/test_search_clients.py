"""
Unit tests for search client query handling.

Verifies that MCP clients correctly format queries for their respective APIs.
Tests use mocked HTTP responses to avoid real network calls.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


# ── ArXiv Client Tests ──


class TestArxivClient:
    """Tests for arxiv_client.py query formatting."""

    @pytest.mark.asyncio
    async def test_arxiv_no_duplicate_all_prefix(self):
        """When query already has 'all:' prefix, ArXiv client should NOT add another."""
        from app.services.mcp_clients.arxiv_client import search_arxiv

        # Query from query_builder already has all: prefixes
        query_from_builder = 'all:"biological control" AND all:"thrips"'

        with patch("aiohttp.ClientSession") as mock_session_cls:
            # Create mock response with empty results (we only care about the query sent)
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

            # Verify the search_query param does NOT have 'all:all:'
            call_args = mock_session.get.call_args
            params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][1] if len(call_args[0]) > 1 else None
            
            if params:
                search_query = params.get("search_query", "")
                assert "all:all:" not in search_query, f"Double prefix detected in: {search_query}"

    @pytest.mark.asyncio
    async def test_arxiv_adds_prefix_for_plain_text(self):
        """When query is plain text without field prefix, ArXiv client should add 'all:'."""
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
                assert search_query.startswith("all:"), f"Expected 'all:' prefix in: {search_query}"


# ── Concept Extraction Tests ──


class TestConceptExtraction:
    """Tests for _extract_concepts_from_query in search_service."""

    def test_extract_from_boolean_query(self):
        """Should extract concepts from a boolean-style query."""
        from app.services.search_service import _extract_concepts_from_query

        query = "biological control AND thrips AND strawberry"
        concepts = _extract_concepts_from_query(query)
        
        assert len(concepts) >= 3
        # Check that each concept is present (case-insensitive)
        lower_concepts = [c.lower() for c in concepts]
        assert any("biological control" in c for c in lower_concepts)
        assert any("thrips" in c for c in lower_concepts)
        assert any("strawberry" in c for c in lower_concepts)

    def test_extract_from_plain_text(self):
        """Should extract concepts from plain text descriptions."""
        from app.services.search_service import _extract_concepts_from_query

        query = "pest management soybean efficacy"
        concepts = _extract_concepts_from_query(query)
        assert len(concepts) > 0

    def test_extract_empty_query(self):
        """Empty query should return empty list."""
        from app.services.search_service import _extract_concepts_from_query

        assert _extract_concepts_from_query("") == []
        assert _extract_concepts_from_query("  ") == []

    def test_extract_removes_boolean_operators(self):
        """Boolean operators should not appear in extracted concepts."""
        from app.services.search_service import _extract_concepts_from_query

        query = "(control OR management) AND (pest OR insect) NOT review"
        concepts = _extract_concepts_from_query(query)
        
        for concept in concepts:
            assert concept.upper() != "AND"
            assert concept.upper() != "OR"
            assert concept.upper() != "NOT"
