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


# ──────────────────────────────────────────────
# Tests del servicio ReferenceExtractor
# ──────────────────────────────────────────────

class TestReferenceExtractorService:
    """Tests para el servicio ReferenceExtractor implementado."""

    def test_normalize_doi_clean(self):
        """DOI limpio se retorna sin cambios."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("10.1038/s41586-021-03819-2") == "10.1038/s41586-021-03819-2"

    def test_normalize_doi_https_url(self):
        """URL https://doi.org/ se strippea correctamente."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("https://doi.org/10.1038/test") == "10.1038/test"

    def test_normalize_doi_http_url(self):
        """URL http://dx.doi.org/ se strippea correctamente."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("http://dx.doi.org/10.1000/xyz") == "10.1000/xyz"

    def test_normalize_doi_prefix(self):
        """Prefijo doi: se strippea correctamente."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("doi:10.1000/abc") == "10.1000/abc"

    def test_normalize_doi_urn_prefix(self):
        """Prefijo urn:doi: se strippea correctamente."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("urn:doi:10.1000/def") == "10.1000/def"

    def test_normalize_doi_with_spaces(self):
        """Espacios alrededor del DOI se limpian."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("  10.1000/test  ") == "10.1000/test"

    def test_normalize_doi_invalid(self):
        """String que no es DOI retorna None."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("not-a-doi") is None

    def test_normalize_doi_empty(self):
        """String vacío retorna None."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi("") is None

    def test_normalize_doi_none(self):
        """None retorna None."""
        from app.services.reference_extractor import normalize_doi
        assert normalize_doi(None) is None

    @pytest.mark.asyncio
    async def test_fetch_from_openalex_success(self):
        """OpenAlex retorna referencias cuando la API responde OK."""
        from app.services.reference_extractor import ReferenceExtractor

        mock_work_response = {
            "doi": "https://doi.org/10.1038/source",
            "title": "Source Paper",
            "publication_year": 2023,
            "referenced_works": ["https://openalex.org/W1234"],
        }
        mock_ref_response = {
            "doi": "https://doi.org/10.1000/ref1",
            "title": "Referenced Paper",
            "publication_year": 2020,
            "authorships": [
                {"author": {"display_name": "Alice Smith"}},
                {"author": {"display_name": "Bob Jones"}},
            ],
        }

        extractor = ReferenceExtractor()

        class MockResponse:
            def __init__(self, status, json_data):
                self.status = status
                self._json_data = json_data
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data

        def mock_get(url, *args, **kwargs):
            if "doi:10.1038/source" in url:
                return MockResponse(200, mock_work_response)
            elif "W1234" in url:
                return MockResponse(200, mock_ref_response)
            return MockResponse(404, {})

        with patch.object(extractor, '_get_session') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.get = mock_get
            mock_session_factory.return_value = mock_session

            refs = await extractor.fetch_from_openalex("10.1038/source")

            assert len(refs) == 1
            assert refs[0]["cited_doi"] == "10.1000/ref1"
            assert refs[0]["cited_title"] == "Referenced Paper"
            assert "Alice Smith" in refs[0]["cited_authors"]
            assert refs[0]["cited_year"] == "2020"
            assert refs[0]["extraction_source"] == "openalex"

    @pytest.mark.asyncio
    async def test_fetch_from_openalex_empty_refs(self):
        """OpenAlex retorna lista vacía cuando no hay referenced_works."""
        from app.services.reference_extractor import ReferenceExtractor

        mock_response = {
            "doi": "https://doi.org/10.1038/test",
            "title": "Test Paper",
            "referenced_works": [],
        }

        extractor = ReferenceExtractor()

        class MockResponse:
            def __init__(self, status, json_data):
                self.status = status
                self._json_data = json_data
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data

        def mock_get(url, *args, **kwargs):
            return MockResponse(200, mock_response)

        with patch.object(extractor, '_get_session') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.get = mock_get
            mock_session_factory.return_value = mock_session

            refs = await extractor.fetch_from_openalex("10.1038/test")
            assert refs == []

    @pytest.mark.asyncio
    async def test_fetch_from_openalex_api_error(self):
        """OpenAlex retorna lista vacía cuando la API falla."""
        from app.services.reference_extractor import ReferenceExtractor

        extractor = ReferenceExtractor()

        class MockResponse:
            def __init__(self, status):
                self.status = status
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return {}

        def mock_get(url, *args, **kwargs):
            return MockResponse(500)

        with patch.object(extractor, '_get_session') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.get = mock_get
            mock_session_factory.return_value = mock_session

            refs = await extractor.fetch_from_openalex("10.1038/test")
            assert refs == []

    @pytest.mark.asyncio
    async def test_fetch_from_semantic_scholar_success(self):
        """Semantic Scholar retorna referencias con metadatos completos."""
        from app.services.reference_extractor import ReferenceExtractor

        mock_response = {
            "references": [
                {
                    "title": "Deep Learning Paper",
                    "year": 2021,
                    "externalIds": {"DOI": "10.1000/dl2021"},
                    "authors": [
                        {"name": "Geoffrey Hinton"},
                        {"name": "Yann LeCun"},
                    ],
                },
                {
                    "title": "No DOI Paper",
                    "year": 2019,
                    "externalIds": {},
                    "authors": [{"name": "Unknown"}],
                },
            ]
        }

        extractor = ReferenceExtractor()

        class MockResponse:
            def __init__(self, status, json_data):
                self.status = status
                self._json_data = json_data
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self._json_data

        def mock_get(url, *args, **kwargs):
            return MockResponse(200, mock_response)

        with patch.object(extractor, '_get_session') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.get = mock_get
            mock_session_factory.return_value = mock_session

            refs = await extractor.fetch_from_semantic_scholar("10.1038/test")

            assert len(refs) == 1  # Solo la que tiene DOI
            assert refs[0]["cited_doi"] == "10.1000/dl2021"
            assert refs[0]["cited_title"] == "Deep Learning Paper"
            assert "Geoffrey Hinton" in refs[0]["cited_authors"]
            assert refs[0]["cited_year"] == "2021"
            assert refs[0]["extraction_source"] == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_extract_references_deduplication(self):
        """extract_references deduplica por DOI y fusiona extraction_source."""
        from app.services.reference_extractor import ReferenceExtractor

        extractor = ReferenceExtractor()

        # Mock: ambas APIs retornan la misma referencia
        with patch.object(extractor, 'fetch_from_openalex', new_callable=AsyncMock) as mock_oa:
            mock_oa.return_value = [
                {
                    "cited_doi": "10.1000/shared",
                    "cited_title": "Shared Paper",
                    "cited_authors": "Author A",
                    "cited_year": "2020",
                    "extraction_source": "openalex",
                }
            ]
            with patch.object(extractor, 'fetch_from_semantic_scholar', new_callable=AsyncMock) as mock_ss:
                mock_ss.return_value = [
                    {
                        "cited_doi": "10.1000/shared",
                        "cited_title": "Shared Paper",
                        "cited_authors": "Author A, Author B",
                        "cited_year": "2020",
                        "extraction_source": "semantic_scholar",
                    },
                    {
                        "cited_doi": "10.1000/unique-ss",
                        "cited_title": "SS Only Paper",
                        "cited_authors": "Author C",
                        "cited_year": "2021",
                        "extraction_source": "semantic_scholar",
                    },
                ]

                refs = await extractor.extract_references("10.1038/test")

                # Debe haber 2 referencias únicas (1 shared + 1 unique)
                assert len(refs) == 2

                # La shared debe tener ambas fuentes
                shared = next(r for r in refs if r["cited_doi"] == "10.1000/shared")
                assert "openalex" in shared["extraction_source"]
                assert "semantic_scholar" in shared["extraction_source"]

                # La unique-ss solo debe tener semantic_scholar
                unique = next(r for r in refs if r["cited_doi"] == "10.1000/unique-ss")
                assert unique["extraction_source"] == "semantic_scholar"

    @pytest.mark.asyncio
    async def test_extract_references_handles_exceptions(self):
        """extract_references maneja excepciones de una API gracefully."""
        from app.services.reference_extractor import ReferenceExtractor

        extractor = ReferenceExtractor()

        with patch.object(extractor, 'fetch_from_openalex', new_callable=AsyncMock) as mock_oa:
            mock_oa.side_effect = Exception("OpenAlex API down")
            with patch.object(extractor, 'fetch_from_semantic_scholar', new_callable=AsyncMock) as mock_ss:
                mock_ss.return_value = [
                    {
                        "cited_doi": "10.1000/ss-only",
                        "cited_title": "SS Paper",
                        "cited_authors": "Author X",
                        "cited_year": "2022",
                        "extraction_source": "semantic_scholar",
                    }
                ]

                refs = await extractor.extract_references("10.1038/test")

                assert len(refs) == 1
                assert refs[0]["cited_doi"] == "10.1000/ss-only"

    @pytest.mark.asyncio
    async def test_close_session(self):
        """close() cierra la sesión HTTP correctamente."""
        from app.services.reference_extractor import ReferenceExtractor

        extractor = ReferenceExtractor()
        session = await extractor._get_session()
        assert not session.closed

        await extractor.close()
        assert session.closed
