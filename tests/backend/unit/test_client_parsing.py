"""
Archivo: test_client_parsing.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias exhaustivas para los mecanismos de parsing de respuestas 
de las APIs científicas integradas (OpenAlex, CrossRef, ArXiv, SciELO, OAI-PMH). 
Asegura que los datos heterogéneos se normalicen correctamente al formato 
estándar de AgriSearch, preservando la integridad de DOIs, autores y metadatos OA.

Acciones Principales:
    - Validación de cumplimiento del formato estándar (REQUIRED_KEYS).
    - Verificación de lógica específica por fuente (reconstrucción de abstracts, limpieza de HTML).
    - Prueba de fallbacks y manejo de campos nulos o malformados.
    - Validación de normalización de DOIs y URLs de PDF.

Estructura Interna:
    - `TestOpenAlexParsing`: Pruebas del motor de OpenAlex.
    - `TestCrossRefParsing`: Pruebas de la integración con Crossref.
    - `TestArXivParsing`: Pruebas de transformación de XML de ArXiv.

Entradas / Dependencias:
    - `app.services.mcp_clients`: Clientes bajo prueba.
    - Fixtures de `conftest.py`.

Salidas / Efectos:
    - Reporte de conformidad de los parsers con el contrato de datos del sistema.
    - Asegura la estabilidad de la capa de ingesta de datos ante cambios en APIs externas.

Ejecución:
    pytest tests/backend/unit/test_client_parsing.py
"""

import pytest
import xml.etree.ElementTree as ET
from app.services.mcp_clients.openalex_client import _parse_openalex_work
from app.services.mcp_clients.crossref_client import _parse_crossref_work
from app.services.mcp_clients.arxiv_client import _parse_arxiv_entry
from app.services.mcp_clients.scielo_client import _parse_scielo_work
from app.services.mcp_clients.oaipmh_client import _parse_oai_record

# Claves requeridas en el formato estándar de salida
REQUIRED_KEYS = {
    "doi", "title", "authors", "year", "abstract",
    "journal", "url", "keywords", "external_id", "open_access_url",
}


def _assert_standard_format(result: dict, source: str) -> None:
    """Verifica que el resultado tenga todas las claves del formato estándar."""
    for key in REQUIRED_KEYS:
        assert key in result, f"[{source}] Falta clave '{key}' en resultado"
    assert isinstance(result["title"], str), f"[{source}] title no es string"
    assert len(result["title"]) > 0, f"[{source}] title está vacío"


class TestOpenAlexParsing:
    """Tests de parsing de OpenAlex."""

    def test_parse_openalex_work_basic(self, sample_openalex_work):
        """Parsea un work estándar de OpenAlex con todos los campos."""
        result = _parse_openalex_work(sample_openalex_work)
        _assert_standard_format(result, "OpenAlex")
        assert result["doi"] == "10.1234/test.oa"
        assert result["year"] == 2023
        assert result["journal"] == "Remote Sensing of Environment"
        assert result["open_access_url"] == "https://example.com/paper.pdf"

    def test_parse_openalex_doi_strips_prefix(self):
        """El DOI de OpenAlex tiene prefijo 'https://doi.org/' que se elimina."""
        work = {"doi": "https://doi.org/10.1234/example", "title": "Test"}
        result = _parse_openalex_work(work)
        assert result["doi"] == "10.1234/example"

    def test_parse_openalex_no_doi(self):
        """Works sin DOI devuelven doi=None."""
        work = {"title": "No DOI Article", "id": "https://openalex.org/W999"}
        result = _parse_openalex_work(work)
        assert result["doi"] is None

    def test_parse_openalex_reconstructs_abstract_from_inverted_index(self, sample_openalex_work):
        """Reconstruye abstract desde el inverted index de OpenAlex."""
        result = _parse_openalex_work(sample_openalex_work)
        assert result["abstract"] is not None
        assert "NDVI" in result["abstract"]
        assert "study" in result["abstract"]

    def test_parse_openalex_keywords_fallback_to_concepts(self):
        """Si no hay keywords, usa concepts como fallback."""
        work = {
            "title": "Test",
            "keywords": [],
            "concepts": [{"display_name": "Remote Sensing"}, {"display_name": "Agriculture"}],
        }
        result = _parse_openalex_work(work)
        assert "Remote Sensing" in result["keywords"]

    def test_parse_openalex_no_oa_location(self):
        """Sin best_oa_location, open_access_url es None."""
        work = {"title": "Test", "best_oa_location": None}
        result = _parse_openalex_work(work)
        assert result["open_access_url"] is None

    def test_parse_openalex_missing_primary_location(self):
        """Sin primary_location, journal es 'Unknown Journal'."""
        work = {"title": "Test", "primary_location": None}
        result = _parse_openalex_work(work)
        assert result["journal"] == "Unknown Journal"


class TestCrossRefParsing:
    """Tests de parsing de CrossRef."""

    def test_parse_crossref_work_basic(self, sample_crossref_work):
        """Parsea un work estándar de CrossRef."""
        result = _parse_crossref_work(sample_crossref_work)
        _assert_standard_format(result, "CrossRef")
        assert result["doi"] == "10.1234/test.cr"
        assert result["year"] == 2022
        assert result["journal"] == "Journal of Agricultural Science"
        assert "agriculture" in result["keywords"]

    def test_parse_crossref_extracts_doi(self, sample_crossref_work):
        """CrossRef SIEMPRE extrae DOI."""
        result = _parse_crossref_work(sample_crossref_work)
        assert result["doi"] is not None
        assert result["doi"] == "10.1234/test.cr"

    def test_parse_crossref_strips_html_from_abstract(self, sample_crossref_work):
        """El abstract de CrossRef puede contener HTML que se elimina."""
        result = _parse_crossref_work(sample_crossref_work)
        assert "<p>" not in result["abstract"]
        assert "<b>" not in result["abstract"]
        assert "HTML" in result["abstract"]  # El contenido se preserva

    def test_parse_crossref_oa_url_always_none(self, sample_crossref_work):
        """CrossRef NO devuelve OA URL (problema conocido, se resuelve con Unpaywall)."""
        result = _parse_crossref_work(sample_crossref_work)
        assert result["open_access_url"] is None

    def test_parse_crossref_title_is_list(self):
        """CrossRef devuelve título como lista, se toma el primer elemento."""
        work = {"title": ["First Title", "Second Title"], "DOI": "10.1/test"}
        result = _parse_crossref_work(work)
        assert result["title"] == "First Title"

    def test_parse_crossref_year_cascade(self):
        """El año se extrae de published-print > published-online > created."""
        work = {
            "title": ["Test"],
            "DOI": "10.1/test",
            "published-print": {"date-parts": [[None]]},
            "published-online": {"date-parts": [[2023]]},
        }
        result = _parse_crossref_work(work)
        assert result["year"] == 2023

    def test_parse_crossref_authors_given_family(self):
        """CrossRef usa given/family en vez de display_name."""
        work = {
            "title": ["Test"],
            "author": [{"given": "Ana", "family": "Martinez"}],
        }
        result = _parse_crossref_work(work)
        assert "Ana" in result["authors"]
        assert "Martinez" in result["authors"]


class TestArXivParsing:
    """Tests de parsing de ArXiv."""

    def test_parse_arxiv_entry_basic(self, sample_arxiv_xml):
        """Parsea una entrada estándar de ArXiv."""
        root = ET.fromstring(sample_arxiv_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        assert len(entries) == 1
        result = _parse_arxiv_entry(entries[0])
        _assert_standard_format(result, "ArXiv")
        assert result["year"] == 2023
        assert result["journal"] == "arXiv"
        assert result["open_access_url"] is not None
        assert "pdf" in result["open_access_url"]

    def test_parse_arxiv_always_has_pdf_url(self, sample_arxiv_xml):
        """ArXiv siempre genera URL de PDF (es fully OA)."""
        root = ET.fromstring(sample_arxiv_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.findall("atom:entry", ns)[0]
        result = _parse_arxiv_entry(entry)
        assert result["open_access_url"] is not None
        assert "arxiv.org/pdf/" in result["open_access_url"]

    def test_parse_arxiv_fabricates_doi(self, sample_arxiv_xml):
        """ArXiv fabrica DOI como '10.48550/arXiv.{id}' cuando no tiene DOI explícito."""
        root = ET.fromstring(sample_arxiv_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.findall("atom:entry", ns)[0]
        result = _parse_arxiv_entry(entry)
        assert result["doi"] is not None
        assert "10.48550/arXiv." in result["doi"]

    def test_parse_arxiv_strips_version_from_id(self, sample_arxiv_xml):
        """El ID de ArXiv tiene sufijo de versión (v1, v2) que se elimina para el DOI."""
        root = ET.fromstring(sample_arxiv_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.findall("atom:entry", ns)[0]
        result = _parse_arxiv_entry(entry)
        assert "v1" not in result["doi"]

    def test_parse_arxiv_categories_as_keywords(self, sample_arxiv_xml):
        """Las categorías de ArXiv se usan como keywords."""
        root = ET.fromstring(sample_arxiv_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.findall("atom:entry", ns)[0]
        result = _parse_arxiv_entry(entry)
        assert "cs.CV" in result["keywords"]
        assert "eess.IV" in result["keywords"]

    def test_parse_arxiv_newlines_stripped(self):
        """Los newlines en título y abstract se reemplazan por espacios."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/9901.00001v1</id>
                <title>Multi-line
title here</title>
                <summary>Multi-line
abstract here</summary>
                <published>2023-01-01T00:00:00Z</published>
            </entry>
        </feed>"""
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.findall("atom:entry", ns)[0]
        result = _parse_arxiv_entry(entry)
        assert "\n" not in result["title"]
        assert "\n" not in result["abstract"]


class TestSciELOParsing:
    """Tests de parsing de SciELO."""

    def test_parse_scielo_work_basic(self, sample_scielo_item):
        """Parsea un item estándar de SciELO."""
        result = _parse_scielo_work(sample_scielo_item)
        _assert_standard_format(result, "SciELO")
        assert result["doi"] == "10.1590/test.scielo"
        assert result["year"] == 2023

    def test_parse_scielo_multilingual_title_prefers_spanish(self, sample_scielo_item):
        """SciELO prioriza título en español sobre inglés."""
        result = _parse_scielo_work(sample_scielo_item)
        # El título en español tiene prioridad
        assert "Detección" in result["title"] or "enfermedades" in result["title"]

    def test_parse_scielo_multilingual_abstract(self, sample_scielo_item):
        """SciELO extrae abstract en español como primera opción."""
        result = _parse_scielo_work(sample_scielo_item)
        assert result["abstract"] is not None

    def test_parse_scielo_authors_as_list(self, sample_scielo_item):
        """SciELO devuelve autores como lista de strings."""
        result = _parse_scielo_work(sample_scielo_item)
        assert "Garcia" in result["authors"]

    def test_parse_scielo_open_access_pdf(self, sample_scielo_item):
        """SciELO proporciona PDF directo."""
        result = _parse_scielo_work(sample_scielo_item)
        assert result["open_access_url"] is not None
        assert result["open_access_url"].endswith(".pdf")

    def test_parse_scielo_english_only(self):
        """Fallback a inglés si no hay español."""
        item = {
            "ti_en": ["English Title"],
            "ab_en": ["English abstract."],
            "au": ["Author One"],
            "da": "2022",
        }
        result = _parse_scielo_work(item)
        assert result["title"] == "English Title"


class TestOAIPMHParsing:
    """Tests de parsing de OAI-PMH (AgEcon, Organic Eprints)."""

    def test_parse_oai_record_basic(self, sample_oai_record):
        """Parsea un registro Dublin Core estándar."""
        result = _parse_oai_record(sample_oai_record)
        _assert_standard_format(result, "OAI-PMH")
        assert result["year"] == 2022

    def test_parse_oai_record_extracts_doi_from_identifier(self, sample_oai_record):
        """Extrae DOI del campo dc:identifier buscando 'doi.org'."""
        result = _parse_oai_record(sample_oai_record)
        assert result["doi"] == "10.5555/oai.test"

    def test_parse_oai_record_url_from_identifier(self, sample_oai_record):
        """Extrae URL del primer identifier que empieza con 'http'."""
        result = _parse_oai_record(sample_oai_record)
        assert result["url"] is not None
        assert result["url"].startswith("http")

    def test_parse_oai_record_no_journal(self, sample_oai_record):
        """OAI-PMH Dublin Core no tiene campo de journal."""
        result = _parse_oai_record(sample_oai_record)
        assert result["journal"] is None

    def test_parse_oai_record_open_access_url_is_url(self, sample_oai_record):
        """open_access_url se establece igual que url para OAI-PMH."""
        result = _parse_oai_record(sample_oai_record)
        assert result["open_access_url"] == result["url"]

    def test_parse_oai_record_no_doi(self):
        """Registros sin DOI en identifier devuelven doi=None."""
        record = {
            "title": ["No DOI Paper"],
            "creator": ["Author"],
            "date": ["2020"],
            "identifier": ["http://example.com/paper"],
        }
        result = _parse_oai_record(record)
        assert result["doi"] is None
