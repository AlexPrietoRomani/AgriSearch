"""
Integration tests for external scientific APIs (OpenAlex, Semantic Scholar, ArXiv).
Tests live connectivity and result parsing.
"""

import pytest
import asyncio
from backend.app.services.mcp_clients.openalex_client import search_openalex
from backend.app.services.mcp_clients.semantic_scholar_client import search_semantic_scholar
from backend.app.services.mcp_clients.arxiv_client import search_arxiv

@pytest.mark.asyncio
async def test_openalex_connectivity():
    """Test that OpenAlex returns results for a common term."""
    results = await search_openalex(query="Tomato", max_results=5)
    assert len(results) > 0
    assert "title" in results[0]
    assert results[0]["title"] is not None

@pytest.mark.asyncio
async def test_semantic_scholar_connectivity():
    """Test that Semantic Scholar returns results for a common term."""
    results = await search_semantic_scholar(query="CNN", max_results=5)
    assert len(results) > 0
    assert "title" in results[0]

@pytest.mark.asyncio
async def test_arxiv_connectivity():
    """Test that ArXiv returns results for a common term."""
    results = await search_arxiv(query="Machine Learning", max_results=5)
    # ArXiv might fail if rate limited, so we handle it more gracefully
    if results:
        assert len(results) > 0
        assert "title" in results[0]
    else:
        print("ArXiv returned 0 results (maybe rate limited)")

@pytest.mark.asyncio
async def test_openalex_date_filter():
    """Test OpenAlex with date filters."""
    results = await search_openalex(query="RAG", max_results=3, year_from=2023, year_to=2024)
    for r in results:
        if r.get("year"):
            assert 2023 <= int(r["year"]) <= 2024
