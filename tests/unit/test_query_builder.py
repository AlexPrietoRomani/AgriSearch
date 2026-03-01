"""
Unit tests for AgriSearch Query Builder.

Tests the deterministic query generation for each API without any LLM or network calls.
"""

import sys
import os

# Add backend to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.services.query_builder import (
    build_openalex_query,
    build_semantic_scholar_query,
    build_arxiv_query,
    build_all_queries,
)


# ── OpenAlex Tests ──


def test_build_openalex_query_simple():
    """OpenAlex query should be plain text with space-separated concepts."""
    concepts = ["biological control", "thrips", "strawberry"]
    result = build_openalex_query(concepts)
    assert "biological control" in result
    assert "thrips" in result
    assert "strawberry" in result
    # Should NOT contain boolean operators or quotes
    assert "AND" not in result
    assert "OR" not in result
    assert "all:" not in result


def test_build_openalex_query_with_synonyms():
    """OpenAlex should include synonyms as extra terms."""
    concepts = ["biological control", "thrips"]
    synonyms = {
        "biological control": ["biocontrol", "BCA"],
        "thrips": ["Frankliniella occidentalis", "Thysanoptera"],
    }
    result = build_openalex_query(concepts, synonyms)
    assert "biological control" in result
    assert "biocontrol" in result
    assert "thrips" in result
    assert "Frankliniella occidentalis" in result


def test_build_openalex_query_empty_concepts():
    """Empty concepts should produce empty query."""
    result = build_openalex_query([])
    assert result == ""


# ── Semantic Scholar Tests ──


def test_build_semantic_scholar_query_simple():
    """Semantic Scholar should produce clean keyword list."""
    concepts = ["integrated pest management", "soybean"]
    result = build_semantic_scholar_query(concepts)
    assert "integrated pest management" in result
    assert "soybean" in result
    assert "AND" not in result
    assert "all:" not in result


def test_build_semantic_scholar_query_with_synonyms():
    """Semantic Scholar should add one synonym per concept."""
    concepts = ["thrips", "strawberry"]
    synonyms = {
        "thrips": ["Frankliniella", "Thysanoptera"],
        "strawberry": ["Fragaria"],
    }
    result = build_semantic_scholar_query(concepts, synonyms)
    assert "thrips" in result
    assert "Frankliniella" in result
    assert "strawberry" in result
    assert "Fragaria" in result
    # Should NOT add second synonym (only first)
    assert "Thysanoptera" not in result


# ── ArXiv Tests ──


def test_build_arxiv_query_simple():
    """ArXiv query should use all: prefix AND operators."""
    concepts = ["machine learning", "agriculture"]
    result = build_arxiv_query(concepts)
    assert 'all:"machine learning"' in result
    assert 'all:"agriculture"' in result
    assert "AND" in result


def test_build_arxiv_query_with_synonyms():
    """ArXiv should group synonyms with OR inside parentheses."""
    concepts = ["thrips", "strawberry"]
    synonyms = {
        "thrips": ["Frankliniella"],
        "strawberry": ["Fragaria"],
    }
    result = build_arxiv_query(concepts, synonyms)
    # Each concept group should have OR with synonyms
    assert 'all:"thrips"' in result
    assert 'all:"Frankliniella"' in result
    assert "OR" in result
    assert "AND" in result


def test_build_arxiv_no_duplicate_prefix():
    """ArXiv query should NOT produce double 'all:all:' patterns."""
    concepts = ["pest control"]
    result = build_arxiv_query(concepts)
    assert "all:all:" not in result
    assert 'all:"pest control"' in result


def test_build_arxiv_single_concept():
    """Single concept without synonyms should produce simple query."""
    concepts = ["deep learning"]
    result = build_arxiv_query(concepts)
    assert result == 'all:"deep learning"'


# ── build_all_queries Tests ──


def test_build_all_queries_generates_for_each_db():
    """Should generate a different query for each database."""
    concepts = ["biological control", "strawberry"]
    databases = ["openalex", "semantic_scholar", "arxiv"]
    result = build_all_queries(concepts, databases=databases)

    assert "openalex" in result
    assert "semantic_scholar" in result
    assert "arxiv" in result

    # ArXiv should have all: prefix, others should not
    assert "all:" in result["arxiv"]
    assert "all:" not in result["openalex"]
    assert "all:" not in result["semantic_scholar"]


def test_build_all_queries_respects_db_selection():
    """Should only generate queries for selected databases."""
    concepts = ["pest", "crop"]
    result = build_all_queries(concepts, databases=["openalex"])

    assert "openalex" in result
    assert "semantic_scholar" not in result
    assert "arxiv" not in result


def test_build_all_queries_empty_concepts():
    """Empty concepts should return empty strings for each DB."""
    result = build_all_queries([], databases=["openalex", "arxiv"])
    assert result["openalex"] == ""
    assert result["arxiv"] == ""
