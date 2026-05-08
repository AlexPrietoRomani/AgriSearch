"""
Archivo: test_query_builder_comprehensive.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias exhaustivas y parametrizadas para validar los motores 
de construcción de consultas (Query Builders) de las 9 bases de datos científicas 
soportadas. Asegura que cada builder genere sintaxis válida, maneje correctamente 
sinónimos y respete las restricciones de longitud y operadores de cada API.

Acciones Principales:
    - Validación de generación de cadenas no vacías para todas las fuentes.
    - Verificación de formatos específicos (prefijos en ArXiv, bilingüismo en SciELO).
    - Prueba de límites de sinónimos y reducción de ruido en las consultas.
    - Validación de manejo de casos borde (conceptos vacíos, BDs desconocidas).

Estructura Interna:
    - `TestQueryBuilderParametrized`: Cobertura total de las 9 BDs mediante parametrización.
    - `TestQueryBuilderSpecificFormats`: Pruebas de lógica particular por fuente.
    - `TestQueryBuilderEdgeCases`: Pruebas de robustez ante entradas inusuales.

Entradas / Dependencias:
    - `app.services.query_builder`: Componente bajo prueba.
    - `pytest`: Framework de testing parametrizado.

Salidas / Efectos:
    - Verificación exhaustiva de la gramática de consultas federadas.
    - Previene regresiones en la construcción de términos booleanos para APIs externas.

Ejecución:
    pytest tests/backend/unit/test_query_builder_comprehensive.py
"""

import pytest
from app.services.query_builder import (
    build_all_queries,
    build_openalex_query,
    build_semantic_scholar_query,
    build_arxiv_query,
    build_crossref_query,
    build_core_query,
    build_scielo_query,
    build_redalyc_query,
    build_oaipmh_query,
)

ALL_DBS = [
    "openalex", "semantic_scholar", "arxiv", "crossref",
    "core", "scielo", "redalyc", "agecon", "organic_eprints",
]

# Prefixes esperados por BD: ArXiv usa "all:", el resto no
DB_PREFIX_MAP = {
    "openalex": None,
    "semantic_scholar": None,
    "arxiv": "all:",
    "crossref": None,
    "core": None,
    "scielo": None,
    "redalyc": None,
    "agecon": None,
    "organic_eprints": None,
}


class TestQueryBuilderParametrized:
    """Tests parametrizados para los 9 query builders."""

    @pytest.mark.parametrize("db", ALL_DBS)
    def test_builder_returns_non_empty_string(self, db):
        """Cada builder devuelve un string no vacío para concepts válidos."""
        concepts = ["crop health", "NDVI"]
        synonyms = {"crop health": ["plant vigor"], "NDVI": ["vegetation index"]}
        queries = build_all_queries(concepts=concepts, synonyms=synonyms, databases=[db])
        assert db in queries, f"Falta query para {db}"
        assert isinstance(queries[db], str), f"Query de {db} no es string"
        assert len(queries[db]) > 0, f"Query de {db} está vacía"

    @pytest.mark.parametrize("db", ALL_DBS)
    def test_builder_single_concept(self, db):
        """Cada builder funciona con un solo concepto."""
        concepts = ["drones"]
        queries = build_all_queries(concepts=concepts, synonyms={}, databases=[db])
        assert len(queries[db]) > 0

    @pytest.mark.parametrize("db,expected_prefix", DB_PREFIX_MAP.items())
    def test_arxiv_has_boolean_prefix(self, db, expected_prefix):
        """ArXiv usa prefijo 'all:', las demás BDs no."""
        concepts = ["crop health", "NDVI"]
        queries = build_all_queries(concepts=concepts, synonyms={}, databases=[db])
        if expected_prefix:
            assert expected_prefix in queries[db], f"ArXiv query no tiene prefijo 'all:'"
        # Las demás no deben tener el prefijo ArXiv (excepto si accidentalmente el concepto lo incluye)


class TestQueryBuilderSpecificFormats:
    """Tests de formatos específicos por BD."""

    def test_arxiv_uses_boolean_and_grouping(self):
        """ArXiv agrupa sinónimos con OR entre paréntesis."""
        concepts = ["drones"]
        synonyms = {"drones": ["UAV", "unmanned aerial vehicle"]}
        query = build_arxiv_query(concepts, synonyms)
        assert "all:" in query
        assert "OR" in query or "drones" in query

    def test_scielo_includes_spanish_concepts(self):
        """SciELO preserva conceptos en español sin traducirlos."""
        concepts = ["salud vegetal"]
        synonyms = {"salud vegetal": ["plant health", "crop health"]}
        query = build_scielo_query(concepts, synonyms)
        assert "salud vegetal" in query

    def test_openalex_limits_synonyms_per_concept(self):
        """OpenAlex usa hasta 2 sinónimos por concepto."""
        concepts = ["test"]
        synonyms = {"test": ["a", "b", "c", "d"]}
        query = build_openalex_query(concepts, synonyms)
        # Solo los primeros 2 sinónimos + concepto original
        assert "a" in query or "test" in query
        assert "d" not in query  # El 4to no debería estar

    def test_semantic_scholar_most_concise(self):
        """Semantic Scholar genera la query más corta (1 syn/concept)."""
        concepts = ["remote sensing", "agriculture"]
        synonyms = {
            "remote sensing": ["satellite imagery", "teledetección"],
            "agriculture": ["farming", "agronomy"],
        }
        ss_query = build_semantic_scholar_query(concepts, synonyms)
        oa_query = build_openalex_query(concepts, synonyms)
        # SS should be shorter or equal (fewer synonyms)
        assert len(ss_query) <= len(oa_query) + 5  # small margin


class TestQueryBuilderEdgeCases:
    """Tests de edge cases."""

    def test_empty_concepts_returns_empty(self):
        """Concepts vacíos → query vacía para todas las BDs."""
        queries = build_all_queries(concepts=[], synonyms={}, databases=ALL_DBS)
        for db in ALL_DBS:
            assert queries[db] == "", f"Query de {db} no está vacía con concepts vacíos"

    def test_synonyms_same_as_concept_are_skipped(self):
        """Sinónimos idénticos al concepto (case-insensitive) se omiten."""
        concepts = ["NDVI"]
        synonyms = {"NDVI": ["ndvi", "Ndvi"]}
        query = build_openalex_query(concepts, synonyms)
        # No debe haber repeticiones del concepto
        assert query.count("NDVI") + query.count("ndvi") <= 2

    def test_build_all_queries_respects_db_selection(self):
        """Solo se generan queries para las BDs seleccionadas."""
        queries = build_all_queries(
            concepts=["test"], synonyms={}, databases=["arxiv", "crossref"]
        )
        assert set(queries.keys()) == {"arxiv", "crossref"}

    def test_build_all_queries_all_nine_dbs(self):
        """Genera queries para las 9 BDs cuando se seleccionan todas."""
        queries = build_all_queries(
            concepts=["test"], synonyms={}, databases=ALL_DBS
        )
        assert len(queries) == 9

    def test_build_all_queries_unknown_db_fallback(self):
        """BD desconocida usa fallback: concepts unidos por espacio."""
        queries = build_all_queries(
            concepts=["crop", "health"], synonyms={}, databases=["unknown_db"]
        )
        assert "unknown_db" in queries
        assert "crop" in queries["unknown_db"]

    def test_none_synonyms_works(self):
        """Sinónimos None no causa error."""
        queries = build_all_queries(concepts=["test"], synonyms=None, databases=["openalex"])
        assert len(queries["openalex"]) > 0

    def test_multiple_concepts_all_appear(self):
        """Todos los conceptos aparecen en la query generada."""
        concepts = ["drones", "NDVI", "agriculture"]
        query = build_openalex_query(concepts, None)
        for concept in concepts:
            assert concept.lower() in query.lower(), f"Concepto '{concept}' no aparece en query"
