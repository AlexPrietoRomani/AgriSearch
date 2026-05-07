"""
Archivo: query_builder.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Constructor determinista de consultas para múltiples APIs de bases de datos científicas.
Transforma conceptos y sinónimos estructurados en cadenas de búsqueda optimizadas
según las reglas sintácticas de cada proveedor (OpenAlex, ArXiv, Crossref, etc.).
No realiza llamadas a LLM; es una capa lógica pura.

Acciones Principales:
    - Generación de consultas booleanas para ArXiv (con prefijos de campo).
    - Optimización de términos de búsqueda para motores de texto completo (OpenAlex, Semantic Scholar).
    - Manejo de sinónimos para expandir la cobertura de búsqueda sin introducir ruido.
    - Adaptación de sintaxis para recolectores OAI-PMH.

Estructura Interna:
    - `build_openalex_query`: Optimizado para búsqueda por relevancia.
    - `build_arxiv_query`: Utiliza lógica booleana estricta (AND/OR).
    - `build_all_queries`: Orquestador que retorna un mapeo de consultas por base de datos.

Entradas / Dependencias:
    - Conceptos y sinónimos extraídos previamente (vía `llm_service`).

Ejemplo de Integración:
    queries = build_all_queries(concepts=["maíz", "sequía"], databases=["arxiv", "openalex"])
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_openalex_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta para la API de OpenAlex.

    OpenAlex utiliza un parámetro `search` de texto completo. No soporta operadores booleanos
    complejos, por lo que se priorizan frases clave limpias separadas por espacios.

    Args:
        concepts (list[str]): Conceptos principales.
        synonyms (dict[str, list[str]] | None): Sinónimos para expandir conceptos.

    Returns:
        str: Cadena de búsqueda optimizada.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            # Add up to 2 synonyms per concept for breadth without noise
            for syn in synonyms[concept][:2]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("OpenAlex query built: %s", query)
    return query


def build_semantic_scholar_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta para la API de Semantic Scholar.

    Semantic Scholar funciona mejor con consultas concisas. No soporta lógica booleana anidada.

    Args:
        concepts (list[str]): Conceptos principales.
        synonyms (dict[str, list[str]] | None): Sinónimos asociados.

    Returns:
        str: Cadena de búsqueda.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            # Add the first synonym only — SS works best with concise queries
            for syn in synonyms[concept][:1]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("Semantic Scholar query built: %s", query)
    return query


def build_arxiv_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta booleana para la API de ArXiv.

    Requiere prefijos de campo (`all:`) y soporta operadores AND/OR. Los sinónimos
    de un mismo concepto se agrupan con OR.

    Args:
        concepts (list[str]): Conceptos principales (se unen con AND).
        synonyms (dict[str, list[str]] | None): Sinónimos (se unen con OR dentro de cada concepto).

    Returns:
        str: Consulta booleana con prefijos ArXiv.
    """
    concept_groups: list[str] = []

    for concept in concepts:
        # Build a group: the concept plus its synonyms joined with OR
        group_terms = [f'all:"{concept}"']
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:2]:
                if syn.lower() != concept.lower():
                    group_terms.append(f'all:"{syn}"')

        if len(group_terms) == 1:
            concept_groups.append(group_terms[0])
        else:
            concept_groups.append(f"({' OR '.join(group_terms)})")

    query = " AND ".join(concept_groups) if concept_groups else ""
    logger.info("ArXiv query built: %s", query)
    return query


def build_crossref_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta para la API de Crossref (via habanero).

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos asociados.

    Returns:
        str: Cadena de búsqueda separada por espacios.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:1]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("Crossref query built: %s", query)
    return query


def build_core_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta para la API de CORE v3.

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos asociados.

    Returns:
        str: Cadena de búsqueda.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:1]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("CORE query built: %s", query)
    return query


def build_scielo_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta optimizada para SciELO.

    Incluye términos tanto en español como en inglés si están disponibles en los sinónimos.

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos.

    Returns:
        str: Cadena de búsqueda.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:2]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("SciELO query built: %s", query)
    return query


def build_redalyc_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta para la API de Redalyc.

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos.

    Returns:
        str: Cadena de búsqueda.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:1]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("Redalyc query built: %s", query)
    return query


def build_oaipmh_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una cadena de términos para filtrado local de registros OAI-PMH.

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos.

    Returns:
        str: Cadena de búsqueda.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:1]:
                if syn.lower() != concept.lower():
                    terms.append(syn)

    query = " ".join(terms)
    logger.info("OAI-PMH query built: %s", query)
    return query


def build_all_queries(
    concepts: list[str],
    synonyms: dict[str, list[str]] | None = None,
    databases: list[str] | None = None,
) -> dict[str, str]:
    """
    Orquesta la generación de consultas optimizadas para todas las bases de datos seleccionadas.

    Args:
        concepts (list[str]): Conceptos base de la investigación.
        synonyms (dict[str, list[str]] | None): Sinónimos por concepto.
        databases (list[str] | None): Lista de bases de datos objetivo. Si es None, genera para todas.

    Returns:
        dict[str, str]: Mapeo de {nombre_db: consulta_especifica}.
    """
    if not databases:
        databases = ["openalex", "semantic_scholar", "arxiv", "crossref",
                     "core", "scielo", "redalyc", "agecon", "organic_eprints"]

    if not concepts:
        logger.warning("No concepts provided for query building")
        return {db: "" for db in databases}

    builders = {
        "openalex": build_openalex_query,
        "semantic_scholar": build_semantic_scholar_query,
        "arxiv": build_arxiv_query,
        "crossref": build_crossref_query,
        "core": build_core_query,
        "scielo": build_scielo_query,
        "redalyc": build_redalyc_query,
        "agecon": build_oaipmh_query,
        "organic_eprints": build_oaipmh_query,
    }

    queries: dict[str, str] = {}
    for db in databases:
        builder = builders.get(db)
        if builder:
            queries[db] = builder(concepts, synonyms)
        else:
            logger.warning("No query builder for database: %s", db)
            # Fallback: simple space-separated concepts
            queries[db] = " ".join(concepts)

    return queries
