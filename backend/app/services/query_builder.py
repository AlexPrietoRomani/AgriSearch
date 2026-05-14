"""
Archivo: query_builder.py
Modificación: 2026-05-14
Autor: Alex Prieto

Descripción:
Constructor determinista de consultas para múltiples APIs de bases de datos científicas.
Transforma conceptos y sinónimos estructurados en cadenas de búsqueda optimizadas
según las reglas sintácticas de cada proveedor (OpenAlex, ArXiv, Crossref, etc.).
No realiza llamadas a LLM; es una capa lógica pura.

Acciones Principales:
    - Generación de consultas booleanas para ArXiv (con prefijos de campo).
    - Optimización de términos de búsqueda para motores de texto completo.
    - Manejo de sinónimos para expandir la cobertura de búsqueda sin introducir ruido.
    - Adaptación de sintaxis para recolectores OAI-PMH.

Estructura Interna:
    - `build_openalex_query`: Optimizado para búsqueda por relevancia.
    - `build_arxiv_query`: Utiliza lógica booleana estricta (AND/OR).
    - `build_all_queries`: Orquestador que retorna mapeo de consultas por BD.

Entradas / Dependencias:
    - Conceptos y sinónimos extraídos previamente (vía `llm_service`).

Salidas / Efectos:
    - Retorna un diccionario con las cadenas de consulta formateadas para cada API.
    - No produce efectos secundarios ni llamadas de red; es una función pura.

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


def build_semantic_scholar_query(
    concepts: list[str], synonyms: dict[str, list[str]] | None = None
) -> str:
    """
    Construye una consulta para la API de Semantic Scholar.

    Semantic Scholar utiliza un motor de relevancia semántica (S2) que NO interpreta
    operadores booleanos explícitos. El mejor rendimiento se obtiene con los términos
    principales separados por espacios, sin sinónimos redundantes, ya que el motor
    los expande automáticamente usando embeddings.

    Args:
        concepts (list[str]): Conceptos principales (se toma solo el primario de cada grupo).
        synonyms (dict[str, list[str]] | None): No utilizado directamente; S2 maneja
            la expansión semántica internamente.

    Returns:
        str: Cadena de búsqueda con los conceptos primarios separados por espacios.
    """
    # S2 usa relevancia semántica; incluir sinónimos produce ruido, no mejora recall
    query = " ".join(concepts)
    logger.info("Semantic Scholar query built: %s", query)
    return query


def build_arxiv_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Construye una consulta booleana para la API de ArXiv.

    Requiere prefijos de campo (`all:`) y soporta operadores AND/OR. Los sinónimos
    de un mismo concepto se agrupan con OR.

    NOTA TÉCNICA: Las comillas dentro de `all:"frase"` se codifican como `%22` por
    urllib.parse.quote, lo que impide que ArXiv las interprete como delimitadores de
    frase exacta. Por tanto, se usa la sintaxis `all:frase+multipalabra` (sin comillas)
    que ArXiv acepta correctamente y aplica lógica AND entre las palabras.

    Args:
        concepts (list[str]): Conceptos principales (se unen con AND).
        synonyms (dict[str, list[str]] | None): Sinónimos (se unen con OR dentro de cada concepto).

    Returns:
        str: Consulta booleana con prefijos ArXiv, sin comillas (URL-safe).
    """
    concept_groups: list[str] = []

    for concept in concepts:
        # Usa all:term sin comillas; ArXiv interpreta espacios como AND entre palabras del campo
        group_terms = [f"all:{concept}"]
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:5]:  # Hasta 5 sinónimos; refleja grupos OR completos de la query maestra
                if syn.lower() != concept.lower():
                    group_terms.append(f"all:{syn}")

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


def build_scielo_query(
    concepts: list[str], synonyms: dict[str, list[str]] | None = None
) -> str:
    """
    Construye una consulta Lucene booleana para la API de SciELO.

    SciELO (basado en Solr/Lucene) acepta operadores AND, OR y frases entre comillas.
    La estrategia óptima es crear grupos OR para sinónimos de cada concepto y unir
    los grupos con AND, replicando fielmente la estructura de la query maestra.

    Args:
        concepts (list[str]): Conceptos principales (uno por grupo AND).
        synonyms (dict[str, list[str]] | None): Sinónimos de cada concepto (forman el OR interno).

    Returns:
        str: Consulta booleana Lucene lista para el parámetro `q=` de SciELO.
    """
    concept_groups: list[str] = []

    for concept in concepts:
        # Construye el grupo OR: concepto principal + sus sinónimos entre comillas
        group_terms = [f'"{concept}"']
        if synonyms and concept in synonyms:
            for syn in synonyms[concept][:5]:
                if syn.lower() != concept.lower():
                    group_terms.append(f'"{syn}"')

        if len(group_terms) == 1:
            concept_groups.append(group_terms[0])
        else:
            concept_groups.append(f"({' OR '.join(group_terms)})")

    query = " AND ".join(concept_groups) if concept_groups else ""
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


def build_oaipmh_query(
    concepts: list[str], synonyms: dict[str, list[str]] | None = None
) -> str:
    """
    Construye una cadena de términos para el filtrado local de registros OAI-PMH.

    OAI-PMH no soporta búsqueda por keywords en el protocolo; el filtrado se realiza
    localmente comparando los términos contra el título y abstract de cada registro.
    Por ello se incluyen todos los términos relevantes (conceptos + sinónimos) para
    maximizar el recall de coincidencias locales.

    Args:
        concepts (list[str]): Conceptos clave.
        synonyms (dict[str, list[str]] | None): Sinónimos para ampliar la cobertura del filtro local.

    Returns:
        str: Cadena de todos los términos separados por espacio para filtrado local.
    """
    terms: list[str] = []
    for concept in concepts:
        terms.append(concept)
        if synonyms and concept in synonyms:
            # Incluye todos los sinónimos para maximizar el recall en el filtro local
            for syn in synonyms[concept]:
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
