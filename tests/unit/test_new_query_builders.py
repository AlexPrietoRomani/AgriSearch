"""
Unit tests for new database query builders (Crossref, CORE, SciELO, Redalyc, OAI-PMH).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.services.query_builder import (
    build_crossref_query,
    build_core_query,
    build_scielo_query,
    build_redalyc_query,
    build_oaipmh_query,
    build_all_queries,
)


# ── Crossref Tests ──


def test_build_crossref_query_simple():
    """Crossref should produce plain text keywords."""
    concepts = ["precision agriculture", "variety trial"]
    result = build_crossref_query(concepts)
    assert "precision agriculture" in result
    assert "variety trial" in result
    assert "all:" not in result
    assert "AND" not in result


def test_build_crossref_query_with_synonyms():
    """Crossref should include one synonym per concept."""
    concepts = ["pest management"]
    synonyms = {"pest management": ["IPM", "integrated pest management"]}
    result = build_crossref_query(concepts, synonyms)
    assert "pest management" in result
    assert "IPM" in result


# ── CORE Tests ──


def test_build_core_query_simple():
    concepts = ["machine learning", "crop yield"]
    result = build_core_query(concepts)
    assert "machine learning" in result
    assert "crop yield" in result


def test_build_core_query_empty():
    result = build_core_query([])
    assert result == ""


# ── SciELO Tests ──


def test_build_scielo_query_simple():
    concepts = ["agricultura de precisión", "ensayo de variedades"]
    result = build_scielo_query(concepts)
    assert "agricultura de precisión" in result
    assert "ensayo de variedades" in result


def test_build_scielo_query_with_synonyms():
    """SciELO should include up to 2 synonyms (bilingual support)."""
    concepts = ["biological control"]
    synonyms = {"biological control": ["control biológico", "biocontrol"]}
    result = build_scielo_query(concepts, synonyms)
    assert "biological control" in result
    assert "control biológico" in result
    assert "biocontrol" in result


# ── Redalyc Tests ──


def test_build_redalyc_query_simple():
    concepts = ["soybean", "pest resistance"]
    result = build_redalyc_query(concepts)
    assert "soybean" in result
    assert "pest resistance" in result


# ── OAI-PMH Tests ──


def test_build_oaipmh_query_simple():
    concepts = ["agroquímico", "pesticide trial"]
    result = build_oaipmh_query(concepts)
    assert "agroquímico" in result
    assert "pesticide trial" in result


# ── build_all_queries with new DBs ──


def test_build_all_queries_includes_new_dbs():
    """build_all_queries should generate for all 9 databases."""
    concepts = ["pest", "crop"]
    databases = ["openalex", "semantic_scholar", "arxiv", "crossref",
                 "core", "scielo", "redalyc", "agecon", "organic_eprints"]
    result = build_all_queries(concepts, databases=databases)

    assert len(result) == 9
    for db in databases:
        assert db in result
        assert len(result[db]) > 0  # Non-empty query


def test_build_all_queries_only_selected():
    """Should only generate for selected databases."""
    concepts = ["test"]
    result = build_all_queries(concepts, databases=["crossref", "scielo"])
    assert "crossref" in result
    assert "scielo" in result
    assert "openalex" not in result


def test_build_all_queries_arxiv_has_prefix():
    """ArXiv should have all: prefix, others should not."""
    concepts = ["deep learning"]
    databases = ["arxiv", "crossref", "core"]
    result = build_all_queries(concepts, databases=databases)
    assert "all:" in result["arxiv"]
    assert "all:" not in result["crossref"]
    assert "all:" not in result["core"]
