"""
Unit tests for new database clients (Crossref, CORE, SciELO, Redalyc, OAI-PMH).

Uses mocks to avoid actual API calls during testing.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
import json


# ── Crossref Client Tests ──


class TestCrossrefClient:

    def test_parse_crossref_work_basic(self):
        """Test parsing a Crossref work dict."""
        from app.services.mcp_clients.crossref_client import _parse_crossref_work

        work = {
            "DOI": "10.1234/test.2024",
            "title": ["Precision Agriculture: A Review"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "published-print": {"date-parts": [[2024]]},
            "abstract": "<p>This is an <b>abstract</b> about precision agriculture.</p>",
            "container-title": ["Journal of Agricultural Science"],
            "subject": ["Agriculture", "Technology"],
        }

        result = _parse_crossref_work(work)
        assert result["doi"] == "10.1234/test.2024"
        assert result["title"] == "Precision Agriculture: A Review"
        assert "John Doe" in result["authors"]
        assert "Jane Smith" in result["authors"]
        assert result["year"] == 2024
        # HTML tags should be stripped from abstract
        assert "<p>" not in result["abstract"]
        assert "<b>" not in result["abstract"]
        assert "abstract" in result["abstract"].lower()
        assert result["journal"] == "Journal of Agricultural Science"
        assert "Agriculture" in result["keywords"]

    def test_parse_crossref_work_missing_fields(self):
        """Test parsing with minimal fields."""
        work = {"DOI": "10.9999/minimal", "title": ["Minimal Work"]}
        from app.services.mcp_clients.crossref_client import _parse_crossref_work

        result = _parse_crossref_work(work)
        assert result["doi"] == "10.9999/minimal"
        assert result["title"] == "Minimal Work"
        assert result["year"] is None
        assert result["authors"] == ""


# ── CORE Client Tests ──


class TestCoreClient:

    def test_parse_core_work_basic(self):
        """Test parsing a CORE work dict."""
        from app.services.mcp_clients.core_client import _parse_core_work

        item = {
            "id": 123456,
            "doi": "10.5678/core.test",
            "title": "Open Access in Agriculture",
            "authors": [{"name": "Carlos Garcia"}, {"name": "Maria Lopez"}],
            "publishedDate": "2023-06-15",
            "abstract": "An overview of open access in agriculture.",
            "downloadUrl": "https://core.ac.uk/download/pdf/123.pdf",
        }

        result = _parse_core_work(item)
        assert result["doi"] == "10.5678/core.test"
        assert result["title"] == "Open Access in Agriculture"
        assert "Carlos Garcia" in result["authors"]
        assert result["year"] == 2023
        assert result["open_access_url"] == "https://core.ac.uk/download/pdf/123.pdf"

    def test_parse_core_work_string_authors(self):
        """CORE sometimes returns authors as strings."""
        item = {
            "title": "Test",
            "authors": ["Alice", "Bob"],
            "yearPublished": 2022,
        }
        from app.services.mcp_clients.core_client import _parse_core_work

        result = _parse_core_work(item)
        assert "Alice" in result["authors"]
        assert "Bob" in result["authors"]
        assert result["year"] == 2022


# ── SciELO Client Tests ──


class TestScieloClient:

    def test_parse_scielo_work_multilingual(self):
        """Test SciELO with multilingual fields."""
        from app.services.mcp_clients.scielo_client import _parse_scielo_work

        item = {
            "ti_es": ["Control biológico de plagas en fresa"],
            "ti_en": ["Biological pest control in strawberry"],
            "ab_en": ["This study evaluates biological control."],
            "au": ["García, Carlos", "López, María"],
            "da": "2023",
            "doi": "10.1590/scielo.2023",
            "ta": ["Revista de Protección Vegetal"],
            "kw": ["biological control", "strawberry", "pest"],
        }

        result = _parse_scielo_work(item)
        # Should pick Spanish title first
        assert "Control biológico" in result["title"]
        assert "García, Carlos" in result["authors"]
        assert result["year"] == 2023
        assert result["doi"] == "10.1590/scielo.2023"

    def test_parse_scielo_work_english_only(self):
        """If no Spanish title, English title should be used."""
        from app.services.mcp_clients.scielo_client import _parse_scielo_work

        item = {
            "ti_en": ["English Only Title"],
            "au": ["Smith, John"],
        }
        result = _parse_scielo_work(item)
        assert result["title"] == "English Only Title"


# ── OAI-PMH Client Tests ──


class TestOaipmhClient:

    def test_parse_oai_record_basic(self):
        """Test parsing OAI-PMH Dublin Core metadata."""
        from app.services.mcp_clients.oaipmh_client import _parse_oai_record

        metadata = {
            "title": ["Agricultural Economics in Latin America"],
            "creator": ["Rodriguez, Ana", "Perez, Luis"],
            "date": ["2023-05-10"],
            "description": ["A comprehensive survey of agri-economics."],
            "subject": ["agriculture", "economics", "Latin America"],
            "identifier": [
                "http://ageconsearch.umn.edu/record/12345",
                "https://doi.org/10.2222/agecon.test",
            ],
        }

        result = _parse_oai_record(metadata)
        assert result["title"] == "Agricultural Economics in Latin America"
        assert "Rodriguez, Ana" in result["authors"]
        assert result["year"] == 2023
        assert result["doi"] == "10.2222/agecon.test"
        assert "http://ageconsearch.umn.edu" in result["url"]
        assert "agriculture" in result["keywords"]

    def test_parse_oai_record_no_doi(self):
        """Test OAI record without DOI in identifiers."""
        from app.services.mcp_clients.oaipmh_client import _parse_oai_record

        metadata = {
            "title": ["No DOI Record"],
            "creator": ["Author A"],
            "date": ["2021"],
            "identifier": ["http://example.org/record/999"],
        }

        result = _parse_oai_record(metadata)
        assert result["doi"] is None
        assert result["url"] == "http://example.org/record/999"
        assert result["year"] == 2021

    def test_oai_endpoints_configured(self):
        """Verify both OAI-PMH endpoints are configured."""
        from app.services.mcp_clients.oaipmh_client import OAI_ENDPOINTS

        assert "agecon" in OAI_ENDPOINTS
        assert "organic_eprints" in OAI_ENDPOINTS
        assert "ageconsearch.umn.edu" in OAI_ENDPOINTS["agecon"]
        assert "orgprints.org" in OAI_ENDPOINTS["organic_eprints"]
