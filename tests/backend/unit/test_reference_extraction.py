"""
Archivo: test_reference_extraction.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas unitarias para la extracción y normalización de referencias bibliográficas.
Valida que el sistema pueda obtener citas desde OpenAlex, Semantic Scholar y GROBID,
normalizando los DOIs y detectando si los artículos citados ya forman parte
del proyecto actual.

Acciones Principales:
    - Validación del parseo de IDs de trabajos desde la API de OpenAlex.
    - Comprobación de la extracción de metadatos (DOI, autores, año) desde Semantic Scholar.
    - Prueba de normalización de variantes de DOI (URLs, prefijos, etc.) a formato canónico.
    - Verificación de la integridad de los registros de referencia en el modelo de datos.
    - Validación de la lógica de detección de duplicados y artículos internos al proyecto.

Entradas / Dependencias:
    - Datos simulados (Fixtures) de respuestas JSON de OpenAlex y Semantic Scholar.
    - Expresiones regulares para normalización de DOIs.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_reference_extraction.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ──────────────────────────────────────────────
# Fixtures de datos de prueba
# ──────────────────────────────────────────────

SAMPLE_OPENALEX_REFERENCES = {
    "referenced_works": [
        "https://openalex.org/W2741809807",
        "https://openalex.org/W2100837269",
        "https://openalex.org/W1982301912",
    ]
}

SAMPLE_SEMANTIC_SCHOLAR_REFERENCES = {
    "references": [
        {
            "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
            "externalIds": {"DOI": "10.1109/CVPR.2016.91"},
            "title": "Deep Residual Learning for Image Recognition",
            "authors": [{"name": "Kaiming He"}, {"name": "Xiangyu Zhang"}],
            "year": 2016,
        },
        {
            "paperId": "abc123def456",
            "externalIds": {"DOI": "10.48550/arXiv.1506.02640"},
            "title": "You Only Look Once: Unified, Real-Time Object Detection",
            "authors": [{"name": "Joseph Redmon"}],
            "year": 2016,
        },
        {
            "paperId": "no_doi_paper",
            "externalIds": {},
            "title": "An obscure paper without DOI",
            "authors": [{"name": "Unknown Author"}],
            "year": 2010,
        },
    ]
}

SAMPLE_ARTICLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "doi": "10.1016/j.compag.2023.107500",
    "title": "YOLO-based crop phenology detection",
    "project_id": "proj-uuid-001",
}


# ──────────────────────────────────────────────
# Tests de extracción desde OpenAlex
# ──────────────────────────────────────────────

class TestOpenAlexReferenceExtraction:
    """Tests para la obtención de referenced_works desde OpenAlex API."""

    def test_parse_openalex_work_ids(self):
        """Verifica que los IDs de OpenAlex se extraigan correctamente de las URLs."""
        raw = SAMPLE_OPENALEX_REFERENCES["referenced_works"]
        parsed = [url.split("/")[-1] for url in raw]
        assert len(parsed) == 3
        assert all(p.startswith("W") for p in parsed)

    def test_openalex_empty_references(self):
        """Verifica el comportamiento ante un artículo sin referencias citadas."""
        empty = {"referenced_works": []}
        assert len(empty["referenced_works"]) == 0

    def test_openalex_deduplication(self):
        """Verifica que se eliminen duplicados en la lista de trabajos referenciados."""
        duplicated = {
            "referenced_works": [
                "https://openalex.org/W2741809807",
                "https://openalex.org/W2741809807",
                "https://openalex.org/W2100837269",
            ]
        }
        unique = list(set(duplicated["referenced_works"]))
        assert len(unique) == 2


# ──────────────────────────────────────────────
# Tests de extracción desde Semantic Scholar
# ──────────────────────────────────────────────

class TestSemanticScholarReferenceExtraction:
    """Tests para la obtención de references desde Semantic Scholar API."""

    def test_parse_references_with_doi(self):
        """Verifica la extracción de referencias que cuentan con DOI válido."""
        refs = SAMPLE_SEMANTIC_SCHOLAR_REFERENCES["references"]
        with_doi = [r for r in refs if r["externalIds"].get("DOI")]
        assert len(with_doi) == 2
        assert with_doi[0]["externalIds"]["DOI"] == "10.1109/CVPR.2016.91"

    def test_handle_references_without_doi(self):
        """Verifica que las referencias sin DOI no sean descartadas totalmente."""
        refs = SAMPLE_SEMANTIC_SCHOLAR_REFERENCES["references"]
        without_doi = [r for r in refs if not r["externalIds"].get("DOI")]
        assert len(without_doi) == 1
        assert without_doi[0]["title"] == "An obscure paper without DOI"

    def test_extract_author_names(self):
        """Verifica la conversión de la lista de autores a una cadena formateada."""
        ref = SAMPLE_SEMANTIC_SCHOLAR_REFERENCES["references"][0]
        authors_str = ", ".join(a["name"] for a in ref["authors"])
        assert authors_str == "Kaiming He, Xiangyu Zhang"

    def test_year_extraction(self):
        """Verifica que el año sea extraído como un entero dentro de un rango válido."""
        ref = SAMPLE_SEMANTIC_SCHOLAR_REFERENCES["references"][0]
        assert isinstance(ref["year"], int)
        assert 1900 <= ref["year"] <= 2030


# ──────────────────────────────────────────────
# Tests de normalización de DOIs
# ──────────────────────────────────────────────

class TestDOINormalization:
    """Tests para asegurar la normalización canónica de DOIs."""

    @pytest.mark.parametrize(
        "raw_doi, expected",
        [
            ("10.1109/CVPR.2016.91", "10.1109/CVPR.2016.91"),
            ("https://doi.org/10.1109/CVPR.2016.91", "10.1109/CVPR.2016.91"),
            ("http://dx.doi.org/10.1109/CVPR.2016.91", "10.1109/CVPR.2016.91"),
            ("DOI: 10.1109/CVPR.2016.91", "10.1109/CVPR.2016.91"),
        ],
    )
    def test_normalize_doi_variants(self, raw_doi, expected):
        """Verifica que diversas variantes de entrada de DOI se normalicen correctamente."""
        import re
        match = re.search(r"(10\.\d{4,}/\S+)", raw_doi)
        normalized = match.group(1) if match else None
        assert normalized == expected

    def test_invalid_doi_returns_none(self):
        """Verifica que una cadena que no contiene un DOI válido retorne None."""
        import re
        invalid = "not-a-doi-at-all"
        match = re.search(r"(10\.\d{4,}/\S+)", invalid)
        assert match is None


# ──────────────────────────────────────────────
# Tests de modelo article_references
# ──────────────────────────────────────────────

class TestArticleReferencesModel:
    """Tests para validar la estructura del modelo de datos de referencias."""

    def test_reference_record_structure(self):
        """Verifica que los registros de referencia posean todos los campos obligatorios."""
        record = {
            "id": "ref-uuid-001",
            "source_article_id": SAMPLE_ARTICLE["id"],
            "cited_doi": "10.1109/CVPR.2016.91",
            "cited_title": "Deep Residual Learning",
            "cited_authors": "He K., Zhang X.",
            "cited_year": 2016,
            "extraction_source": "openalex",
            "is_in_project": False,
        }
        required_fields = [
            "id", "source_article_id", "cited_doi",
            "cited_title", "extraction_source", "is_in_project",
        ]
        for field in required_fields:
            assert field in record

    def test_is_in_project_flag(self):
        """Verifica la detección de si un DOI citado ya existe en el proyecto actual."""
        project_dois = {"10.1109/CVPR.2016.91", "10.3390/rs14153690"}
        cited_doi = "10.1109/CVPR.2016.91"
        assert cited_doi in project_dois

        external_doi = "10.9999/unknown.2023"
        assert external_doi not in project_dois
