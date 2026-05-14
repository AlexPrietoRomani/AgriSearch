"""
Archivo: scielo_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente para la API de búsqueda de SciELO (https://search.scielo.org). 
SciELO es una biblioteca científica electrónica de acceso abierto que cubre 
América Latina y el Caribe. Este cliente permite buscar artículos en múltiples idiomas.

Acciones Principales:
    - Ejecuta búsquedas asíncronas en el motor de búsqueda de SciELO.
    - Maneja respuestas multilingües (español, inglés, portugués).
    - Normaliza los datos al formato estándar de AgriSearch.

Estructura Interna:
    - `_parse_scielo_work`: Parsea documentos multilingües de SciELO.
    - `search_scielo`: Función principal de búsqueda federada.

Entradas / Dependencias:
    - Librería `aiohttp`.
    - Endpoint de búsqueda de SciELO.

Salidas / Efectos:
    - Retorna una lista de artículos con soporte multilingüe normalizado.
    - Realiza llamadas de red asíncronas a search.scielo.org.

Ejemplo de Integración:
    articles = await search_scielo("riego por goteo", max_results=10)
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SCIELO_SEARCH_API = "https://search.scielo.org"


def _parse_scielo_work(item: dict) -> dict[str, Any]:
    """
    Parsea un resultado de búsqueda de SciELO al formato estándar de AgriSearch.

    Maneja campos multilingües para título y abstract, priorizando español e inglés.

    Args:
        item (dict): Diccionario de resultado retornado por SciELO.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Authors
    authors_raw = item.get("au", [])
    if isinstance(authors_raw, list):
        authors = ", ".join(authors_raw[:20])
    else:
        authors = str(authors_raw)

    # Title (may be multilingual)
    title = None
    for lang_key in ["ti_es", "ti_en", "ti_pt", "ti"]:
        t = item.get(lang_key)
        if t:
            title = t[0] if isinstance(t, list) else t
            break
    if not title:
        title = item.get("title", "No Title")
        if isinstance(title, list):
            title = title[0]

    # Abstract
    abstract = None
    for lang_key in ["ab_es", "ab_en", "ab_pt", "ab"]:
        a = item.get(lang_key)
        if a:
            abstract = a[0] if isinstance(a, list) else a
            break

    # Year
    year = None
    pub_year = item.get("da") or item.get("publication_year")
    if pub_year:
        try:
            year = int(str(pub_year)[:4])
        except (ValueError, TypeError):
            pass

    # Keywords
    keywords_raw = item.get("kw", [])
    if isinstance(keywords_raw, list):
        keywords = ", ".join(keywords_raw[:10])
    else:
        keywords = str(keywords_raw)

    # Tipo de documento desde el campo 'tp' (SciELO usa 'research-article', 'review-article', etc.)
    _SCIELO_TYPE_MAP = {
        "research-article": "journal-article",
        "review-article": "journal-article",
        "article": "journal-article",
        "editorial": "other",
        "letter": "other",
        "case-report": "journal-article",
        "brief-report": "journal-article",
        "book": "book",
        "thesis": "thesis",
        "conference": "conference-paper",
    }
    raw_doc_type = item.get("document_type") or item.get("tp")
    if isinstance(raw_doc_type, list):
        raw_doc_type = raw_doc_type[0] if raw_doc_type else None
    doc_type = _SCIELO_TYPE_MAP.get(str(raw_doc_type).lower(), "journal-article") if raw_doc_type else "journal-article"

    return {
        "doi": item.get("doi"),
        "title": title or "No Title",
        "authors": authors,
        "year": year,
        "abstract": abstract,
        "journal": item.get("ta", [None])[0] if isinstance(item.get("ta"), list) else item.get("ta"),
        "url": item.get("ur", [None])[0] if isinstance(item.get("ur"), list) else item.get("ur") or item.get("fulltext_html"),
        "keywords": keywords,
        "external_id": item.get("id") or item.get("pid"),
        "open_access_url": item.get("fulltext_pdf"),
        "document_type": doc_type,
    }


async def search_scielo(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos en SciELO que coincidan con la consulta.

    Intenta primero con la query booleana completa. Si recibe 403 (WAF de SciELO
    bloquea queries complejas), reintenta con una versión simplificada de texto libre.

    Args:
        query (str): Términos de búsqueda (Lucene booleano o texto libre).
        max_results (int): Cantidad máxima de resultados a retornar.
        year_from (int | None): Año inicial del filtro.
        year_to (int | None): Año final del filtro.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    import json as _json

    articles: list[dict[str, Any]] = []

    # Fallback: versión simplificada de texto libre si la booleana da 403
    simple_query = (
        query
        .replace("(", "").replace(")", "")
        .replace(" OR ", " ").replace(" AND ", " ")
        .replace('"', "")
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Referer": "https://search.scielo.org/",
        "Origin": "https://search.scielo.org",
    }

    # Dos intentos: query booleana -> query simple
    queries_to_try = [query, simple_query]

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            for attempt, q in enumerate(queries_to_try):
                params: dict = {
                    "q": q,
                    "output": "json",
                    "count": min(max_results, 100),
                    "from": 0,
                    "lang": "en",
                }
                if year_from:
                    params["filter[year_cluster][]"] = f"{year_from}-{year_to or 2030}"

                async with session.get(f"{SCIELO_SEARCH_API}/", params=params) as resp:
                    if resp.status == 403:
                        logger.warning(
                            "SciELO 403 en intento %d/%d — %s",
                            attempt + 1, len(queries_to_try),
                            "probando query simplificada" if attempt == 0 else "ambas bloqueadas por WAF",
                        )
                        continue
                    if resp.status != 200:
                        logger.warning("SciELO API returned %d en intento %d", resp.status, attempt + 1)
                        continue

                    content_type = resp.headers.get("Content-Type", "")
                    if "json" in content_type:
                        data = await resp.json()
                    else:
                        text = await resp.text()
                        try:
                            data = _json.loads(text)
                        except Exception:
                            logger.warning("SciELO returned non-JSON on attempt %d", attempt + 1)
                            continue

                    # La respuesta puede usar el formato Elasticsearch hits
                    hits = data.get("hits", {}).get("hits", [])
                    # O el formato Solr docs
                    docs = data.get("response", {}).get("docs", [])

                    items = [h.get("_source", {}) for h in hits] if hits else docs

                    for item in items:
                        parsed = _parse_scielo_work(item)
                        if parsed["title"] and parsed["title"] != "No Title":
                            articles.append(parsed)
                        if len(articles) >= max_results:
                            break

                    if articles:
                        break  # No hace falta el fallback

    except Exception as e:
        logger.error("SciELO search failed: %s", str(e))

    logger.info("SciELO: found %d articles for query: %s", len(articles), query[:60])
    return articles[:max_results]
