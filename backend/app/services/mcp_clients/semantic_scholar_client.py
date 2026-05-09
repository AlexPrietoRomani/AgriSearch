"""
Archivo: semantic_scholar_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente para la API de Semantic Scholar (https://api.semanticscholar.org). 
Permite la búsqueda de artículos científicos utilizando el motor de búsqueda 
impulsado por IA de Semantic Scholar, extrayendo metadatos y acceso abierto.

Acciones Principales:
    - Ejecuta búsquedas asíncronas paginadas en Semantic Scholar.
    - Maneja límites de tasa (rate limiting) de la API pública.
    - Normaliza la respuesta del grafo de artículos al formato estándar de AgriSearch.

Estructura Interna:
    - `_parse_ss_paper`: Convierte objeto de Semantic Scholar en esquema interno.
    - `search_semantic_scholar`: Función principal de búsqueda federada.

Entradas / Dependencias:
    - Librería `aiohttp`.
    - API Graph de Semantic Scholar.

Salidas / Efectos:
    - Retorna una lista de artículos normalizados con identificadores de Semantic Scholar.
    - Realiza llamadas de red asíncronas sujetas a rate limits de api.semanticscholar.org.

Ejemplo de Integración:
    articles = await search_semantic_scholar("climate change impact", max_results=25)
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SS_API = "https://api.semanticscholar.org/graph/v1"
SS_FIELDS = "paperId,externalIds,title,authors,year,abstract,venue,url,openAccessPdf,publicationTypes"


def _parse_ss_paper(paper: dict) -> dict[str, Any]:
    """
    Parsea un objeto de artículo de Semantic Scholar al formato estándar de AgriSearch.

    Extrae DOI, autores, título, año, abstract y URL del PDF si está disponible.

    Args:
        paper (dict): Diccionario crudo del artículo retornado por la API.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Extract DOI
    doi = None
    external_ids = paper.get("externalIds", {})
    if external_ids:
        doi = external_ids.get("DOI")

    # Extract authors
    authors = ", ".join(
        a.get("name", "") for a in paper.get("authors", [])[:20]
    )

    # Extract OA URL
    oa_pdf = paper.get("openAccessPdf")
    oa_url = oa_pdf.get("url") if oa_pdf else None

    # Map publicationTypes to internal vocabulary
    _SS_TYPE_MAP = {
        "JournalArticle": "journal-article",
        "Review": "journal-article",
        "Conference": "conference-paper",
        "Book": "book",
        "BookSection": "book-chapter",
        "Thesis": "thesis",
        "Dataset": "dataset",
        "ClinicalTrial": "journal-article",
        "News": "other",
        "LettersAndComments": "journal-article",
    }
    pub_types = paper.get("publicationTypes") or []
    raw_type = pub_types[0] if pub_types else None
    doc_type = _SS_TYPE_MAP.get(raw_type, "journal-article") if raw_type else "journal-article"

    return {
        "doi": doi,
        "title": paper.get("title", "No Title"),
        "authors": authors,
        "year": paper.get("year"),
        "abstract": paper.get("abstract"),
        "journal": paper.get("venue"),
        "url": paper.get("url"),
        "keywords": None,
        "external_id": paper.get("paperId"),
        "open_access_url": oa_url,
        "document_type": doc_type,
    }


async def search_semantic_scholar(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos en Semantic Scholar que coincidan con la consulta.

    Args:
        query (str): Términos de búsqueda.
        max_results (int): Cantidad máxima de resultados a retornar.
        year_from (int | None): Año de inicio del filtro.
        year_to (int | None): Año final del filtro.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    articles: list[dict[str, Any]] = []
    limit = min(max_results, 100)
    offset = 0

    # Build year filter
    year_filter = ""
    if year_from and year_to:
        year_filter = f"&year={year_from}-{year_to}"
    elif year_from:
        year_filter = f"&year={year_from}-"
    elif year_to:
        year_filter = f"&year=-{year_to}"

    try:
        async with aiohttp.ClientSession() as session:
            while len(articles) < max_results:
                params = {
                    "query": query,
                    "limit": limit,
                    "offset": offset,
                    "fields": SS_FIELDS,
                }
                if year_from and year_to:
                    params["year"] = f"{year_from}-{year_to}"
                elif year_from:
                    params["year"] = f"{year_from}-"
                elif year_to:
                    params["year"] = f"-{year_to}"

                async with session.get(f"{SS_API}/paper/search", params=params) as resp:
                    if resp.status == 429:
                        logger.warning("Semantic Scholar rate limited. Stopping pagination.")
                        break
                    if resp.status != 200:
                        logger.warning("Semantic Scholar API returned %d", resp.status)
                        break

                    data = await resp.json()
                    papers = data.get("data", [])

                    if not papers:
                        break

                    for paper in papers:
                        parsed = _parse_ss_paper(paper)
                        if parsed["title"] and parsed["title"] != "No Title":
                            articles.append(parsed)

                    total = data.get("total", 0)
                    offset += limit
                    if offset >= total or offset >= max_results:
                        break

        logger.info("Semantic Scholar: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("Semantic Scholar search failed: %s", str(e))
        raise

    return articles[:max_results]
