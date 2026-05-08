"""
Archivo: openalex_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente para la API REST de OpenAlex (https://api.openalex.org). 
OpenAlex es una de las bases de datos bibliográficas abiertas más completas. 
Este cliente permite realizar búsquedas avanzadas con filtrado por fecha y tipo de artículo.

Acciones Principales:
    - Realiza peticiones asíncronas paginadas a OpenAlex.
    - Normaliza los datos de "works" al formato de AgriSearch.
    - Reconstruye abstracts a partir del "inverted index" de OpenAlex.
    - Extrae información de acceso abierto (OA).

Estructura Interna:
    - `_parse_authors`: Extrae nombres de autores.
    - `_parse_openalex_work`: Transforma objeto "work" en artículo estándar.
    - `_reconstruct_abstract`: Convierte el índice invertido en texto plano.
    - `search_openalex`: Función principal de búsqueda paginada.

Entradas / Dependencias:
    - Librería `aiohttp`.
    - Identificador `MAILTO` para el "polite pool" de OpenAlex.

Salidas / Efectos:
    - Retorna una lista de artículos con metadatos enriquecidos (OA, abstracts reconstruidos).
    - Ejecuta llamadas de red asíncronas al cluster de OpenAlex.

Ejemplo de Integración:
    articles = await search_openalex("regenerative agriculture", max_results=50)
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
MAILTO = "agrisearch@alex-prieto.com"


def _parse_authors(authorships: list[dict]) -> str:
    """
    Extrae los nombres de los autores a partir de la lista de authorships de OpenAlex.

    Args:
        authorships (list[dict]): Lista de diccionarios de autoría.

    Returns:
        str: Nombres de autores separados por comas (límite 20).
    """
    names = []
    for auth in authorships[:20]:  # Limit to 20 authors
        display_name = auth.get("author", {}).get("display_name", "")
        if display_name:
            names.append(display_name)
    return ", ".join(names)


def _parse_openalex_work(work: dict) -> dict[str, Any]:
    """
    Parsea un objeto de trabajo (work) de OpenAlex al formato estándar de AgriSearch.

    Args:
        work (dict): Diccionario crudo de OpenAlex.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Extract OA URL
    oa_url = None
    best_oa = work.get("best_oa_location")
    if best_oa:
        oa_url = best_oa.get("pdf_url") or best_oa.get("landing_page_url")

    # Extract keywords/concepts safely (might be missing if not in select)
    keywords_list = []
    for kw in work.get("keywords", []) or []:
        if isinstance(kw, dict):
            keywords_list.append(kw.get("display_name", ""))
        elif isinstance(kw, str):
            keywords_list.append(kw)
    
    # Fallback to concepts if keywords not present
    if not keywords_list:
        for concept in work.get("concepts", []) or []:
            keywords_list.append(concept.get("display_name", ""))

    return {
        "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
        "title": work.get("title", "No Title"),
        "authors": _parse_authors(work.get("authorships", [])),
        "year": work.get("publication_year"),
        "abstract": work.get("abstract") or _reconstruct_abstract(work.get("abstract_inverted_index")),
        "journal": work.get("primary_location", {}).get("source", {}).get("display_name") if work.get("primary_location") and work.get("primary_location").get("source") else "Unknown Journal",
        "url": work.get("doi") or work.get("id"),
        "keywords": ", ".join(keywords_list[:10]),
        "external_id": work.get("id"),
        "open_access_url": oa_url,
    }


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """
    Reconstruye el abstract a partir del formato de índice invertido de OpenAlex.

    Args:
        inverted_index (dict | None): Índice invertido de palabras y posiciones.

    Returns:
        str | None: Abstract en texto plano o None si no existe.
    """
    if not inverted_index:
        return None
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


async def search_openalex(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos en OpenAlex que coincidan con la consulta.

    Implementa paginación automática y filtrado por fecha directamente en la API.

    Args:
        query (str): Términos de búsqueda.
        max_results (int): Cantidad máxima de resultados a retornar.
        year_from (int | None): Año de inicio del filtro.
        year_to (int | None): Año final del filtro.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    articles: list[dict[str, Any]] = []
    per_page = min(max_results, 50)
    pages_needed = (max_results + per_page - 1) // per_page

    # Build filters (alex-mcp style: focus on quality articles)
    filters = [
        "type:article|journal-article",
        "has_doi:true"
    ]
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")

    try:
        async with aiohttp.ClientSession() as session:
            for page in range(1, pages_needed + 1):
                params = {
                    "search": query,
                    "per_page": per_page,
                    "page": page,
                    "mailto": MAILTO,
                    "filter": ",".join(filters),
                    # Optimization from alex-mcp: limit data transferred
                    "select": "id,doi,title,authorships,publication_year,abstract_inverted_index,primary_location,type,best_oa_location",
                }

                async with session.get(f"{OPENALEX_API}/works", params=params) as resp:
                    logger.info("OpenAlex Request URL: %s", resp.url)
                    if resp.status != 200:
                        logger.warning("OpenAlex API returned %d on page %d", resp.status, page)
                        break

                    data = await resp.json()
                    logger.info("OpenAlex Response Page %d: %d results, metadata: %s", page, len(data.get("results", [])), data.get("meta", {}))
                    works = data.get("results", [])

                    if not works:
                        logger.warning("OpenAlex: No works found in response for query '%s' on page %d", query, page)
                        break

                    for work in works:
                        parsed = _parse_openalex_work(work)
                        if parsed["title"] and parsed["title"] != "No Title":
                            articles.append(parsed)

                    if len(articles) >= max_results:
                        break

        logger.info("OpenAlex: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("OpenAlex search failed: %s", str(e))
        raise

    return articles[:max_results]
