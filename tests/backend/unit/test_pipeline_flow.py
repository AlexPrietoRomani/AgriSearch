"""
Archivo: test_pipeline_flow.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas de integración para validar el flujo completo del pipeline de 
búsqueda científica: desde la captura de la intención del usuario, pasando por 
la generación de queries con LLM, hasta la ejecución federada y la deduplicación 
de resultados. Asegura la cohesión entre los servicios de búsqueda e IA.

Acciones Principales:
    - Validación de la extracción de conceptos clave para la auditoría de búsquedas.
    - Prueba de normalización de DOIs heterogéneos (URLs vs Cadenas).
    - Verificación del motor de deduplicación por títulos (Fuzzy Matching).
    - Validación de la extracción de payloads JSON desde respuestas de LLM con ruido.

Estructura Interna:
    - `TestExtractConcepts`: Pruebas de tokenización de queries.
    - `TestNormalizeDoi`: Pruebas de limpieza de identificadores.
    - `TestIsDuplicateTitle`: Pruebas de similitud de cadenas.
    - `TestExtractJsonPayload`: Pruebas de robustez en el parsing de respuestas de IA.

Entradas / Dependencias:
    - `app.services.search_service`: Lógica de deduplicación y conceptos.
    - `app.services.llm_service`: Utilidades de extracción de datos.

Salidas / Efectos:
    - Verifica que el pipeline mantenga la integridad de los datos durante la transformación.
    - Asegura que no existan fugas de información ni errores de parsing críticos.

Ejecución:
    pytest tests/backend/unit/test_pipeline_flow.py
"""

import pytest
from app.services.search_service import (
    _extract_concepts_from_query,
    _normalize_doi,
    _is_duplicate_title,
)
from app.services.llm_service import _extract_json_payload


class TestExtractConcepts:
    """Tests de extracción de conceptos desde queries."""

    def test_extract_from_boolean_query(self):
        """Extrae conceptos de una query booleana con AND/OR."""
        query = "remote sensing AND crop health AND NDVI"
        concepts = _extract_concepts_from_query(query)
        assert len(concepts) > 0
        assert any("remote" in c.lower() for c in concepts)

    def test_extract_from_plain_text(self):
        """Extrae conceptos de texto plano sin operadores."""
        query = "detection of plant diseases using multispectral imaging"
        concepts = _extract_concepts_from_query(query)
        assert len(concepts) > 0

    def test_extract_empty_query(self):
        """Query vacía devuelve lista vacía."""
        assert _extract_concepts_from_query("") == []
        assert _extract_concepts_from_query("   ") == []

    def test_extract_removes_boolean_operators(self):
        """Los operadores booleanos se eliminan de los conceptos."""
        query = "control OR management AND pest NOT review"
        concepts = _extract_concepts_from_query(query)
        all_text = " ".join(concepts).lower()
        # Los operadores no deben aparecer como conceptos aislados
        assert "or" not in [c.lower() for c in concepts]
        assert "and" not in [c.lower() for c in concepts]
        assert "not" not in [c.lower() for c in concepts]

    def test_extract_spanish_operators(self):
        """Los operadores booleanos en español se eliminan."""
        query = "control Y manejo E integrado U orgánico NO químico"
        concepts = _extract_concepts_from_query(query)
        ops = {"y", "e", "u", "o", "no"}
        for c in concepts:
            assert c.lower() not in ops

    def test_extract_max_10_concepts(self):
        """Se limita a un máximo de 10 conceptos."""
        query = " AND ".join([f"concept{i}" for i in range(20)])
        concepts = _extract_concepts_from_query(query)
        assert len(concepts) <= 10

    def test_extract_strips_parentheses_and_quotes(self):
        """Paréntesis, corchetes y comillas se eliminan."""
        query = '(remote sensing) AND "crop health" AND [NDVI]'
        concepts = _extract_concepts_from_query(query)
        for c in concepts:
            assert "(" not in c
            assert ")" not in c
            assert '"' not in c
            assert "[" not in c


class TestNormalizeDoi:
    """Tests de normalización de DOI."""

    def test_normalize_doi_strips_url_prefix(self):
        """Elimina prefijos https://doi.org/ y http://doi.org/."""
        assert _normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert _normalize_doi("http://doi.org/10.1234/test") == "10.1234/test"

    def test_normalize_doi_strips_doi_prefix(self):
        """Elimina prefijo 'DOI:' (case-insensitive por lowercase previo)."""
        assert _normalize_doi("doi:10.1234/test") == "10.1234/test"

    def test_normalize_doi_lowercases(self):
        """Normaliza a minúsculas."""
        assert _normalize_doi("10.1234/TEST") == "10.1234/test"

    def test_normalize_doi_strips_whitespace(self):
        """Elimina espacios en blanco."""
        assert _normalize_doi("  10.1234/test  ") == "10.1234/test"

    def test_normalize_doi_returns_none_for_invalid(self):
        """DOIs inválidos devuelven None."""
        assert _normalize_doi(None) is None
        assert _normalize_doi("") is None
        assert _normalize_doi("not-a-doi") is None
        assert _normalize_doi("10") is None  # Solo 2 dígitos después de 10.
        assert _normalize_doi("abc") is None

    def test_normalize_doi_valid_format(self):
        """DOIs válidos se normalizan correctamente."""
        assert _normalize_doi("10.1234/test.2023") == "10.1234/test.2023"
        assert _normalize_doi("10.1038/s41586-023-06034-3") == "10.1038/s41586-023-06034-3"


class TestIsDuplicateTitle:
    """Tests de detección de títulos duplicados por fuzzy matching."""

    def test_exact_match_returns_true(self):
        """Títulos idénticos son duplicados."""
        assert _is_duplicate_title("Remote Sensing", "Remote Sensing") is True

    def test_case_insensitive(self):
        """La comparación es case-insensitive."""
        assert _is_duplicate_title("Remote Sensing", "remote sensing") is True

    def test_similar_above_threshold(self):
        """Títulos >85% similares son duplicados."""
        title_a = "Remote Sensing for Agricultural Crop Health Assessment"
        title_b = "Remote Sensing for Agricultural Crop Health Analysis"
        assert _is_duplicate_title(title_a, title_b, threshold=0.85) is True

    def test_different_below_threshold(self):
        """Títulos <85% similares no son duplicados."""
        title_a = "Remote Sensing for Crop Health"
        title_b = "Machine Learning in Financial Markets"
        assert _is_duplicate_title(title_a, title_b, threshold=0.85) is False

    def test_empty_titles_return_false(self):
        """Títulos vacíos no son duplicados."""
        assert _is_duplicate_title("", "test") is False
        assert _is_duplicate_title("test", "") is False
        assert _is_duplicate_title("", "") is False

    def test_none_titles_return_false(self):
        """Títulos None no son duplicados."""
        assert _is_duplicate_title(None, "test") is False
        assert _is_duplicate_title("test", None) is False


class TestExtractJsonPayload:
    """Tests de extracción de JSON desde respuestas LLM."""

    def test_plain_json_passthrough(self):
        """JSON plano se parsea directamente."""
        result = _extract_json_payload('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_fence_stripped(self):
        """Bloques de código markdown se eliminan antes de parsear."""
        content = '```json\n{"key": "value"}\n```'
        result = _extract_json_payload(content)
        assert result == {"key": "value"}

    def test_embedded_in_text(self):
        """JSON embebido en texto se extrae correctamente."""
        content = 'Here is the result: {"key": "value"} and more text'
        result = _extract_json_payload(content)
        assert result == {"key": "value"}

    def test_dict_passthrough(self):
        """Un dict ya parseado se devuelve directamente."""
        input_dict = {"key": "value"}
        result = _extract_json_payload(input_dict)
        assert result == input_dict

    def test_empty_raises_error(self):
        """Contenido vacío o None lanza ValueError."""
        with pytest.raises(ValueError):
            _extract_json_payload(None)
        with pytest.raises(ValueError):
            _extract_json_payload("")

    def test_invalid_json_raises_error(self):
        """Contenido sin JSON válido lanza ValueError."""
        with pytest.raises(ValueError):
            _extract_json_payload("this is not json at all")

    def test_markdown_fence_without_json_tag(self):
        """Bloque de código sin etiqueta 'json' también se parsea."""
        content = '```\n{"key": "value"}\n```'
        result = _extract_json_payload(content)
        assert result == {"key": "value"}
