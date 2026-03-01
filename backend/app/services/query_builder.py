"""
AgriSearch Backend - Deterministic Query Builder.

Constructs API-specific search queries from structured concepts and synonyms.
No LLM calls — pure deterministic functions that format queries for each database API.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_openalex_query(concepts: list[str], synonyms: dict[str, list[str]] | None = None) -> str:
    """
    Build a query for the OpenAlex API.

    OpenAlex uses a simple full-text `search` parameter. Complex boolean operators
    are NOT supported. Best results come from clean keyword phrases separated by spaces.

    Strategy: join main concepts with their top synonyms as space-separated terms.
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
    Build a query for the Semantic Scholar API.

    Semantic Scholar's search endpoint accepts a simple text query.
    It does NOT support nested boolean logic. Keep it simple: primary keywords
    joined with `+` (URL-encoded space) or just spaces.

    Strategy: use main concepts plus the single best synonym for each.
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
    Build a query for the ArXiv API.

    ArXiv requires field prefixes on every term: `all:"term"`.
    Multiple terms are combined with AND/OR operators.

    Strategy: each concept becomes `all:"concept"`, joined with AND.
    Synonyms for a concept are grouped with OR.
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
    Build a query for the Crossref API (via habanero).

    Crossref accepts simple keyword queries. Boolean operators are limited.
    Strategy: join concepts with spaces, include top synonyms.
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
    Build a query for the CORE API v3.

    CORE supports basic keyword search. Strategy: join concepts with spaces.
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
    Build a query for SciELO search.

    SciELO supports keyword search. Strategy: concepts with synonyms,
    separated by spaces. Include both English and Spanish terms when available.
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
    Build a query for Redalyc API.

    Redalyc accepts keyword search. Strategy: clean concepts with synonyms.
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
    Build a query for OAI-PMH harvesting (AgEcon Search, Organic Eprints).

    OAI-PMH doesn't support search queries natively.
    We use the terms for local post-filtering of harvested records.
    Strategy: simple space-separated concepts for matching.
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
    Build optimized queries for all selected databases.

    Returns a dict mapping database name to its specific query string.
    Only builds queries for the databases in the `databases` list.
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
