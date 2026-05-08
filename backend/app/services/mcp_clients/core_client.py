"""
Archivo: core_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente para la API de CORE (https://api.core.ac.uk). 
Permite la búsqueda de artículos de acceso abierto en el agregador CORE, 
el cual recolecta contenido de repositorios institucionales y revistas de todo el mundo.

Acciones Principales:
    - Realiza búsquedas asíncronas en el endpoint v3 de CORE.
    - Normaliza la respuesta de CORE al formato interno de AgriSearch.
    - Maneja la autenticación mediante API Key.

Estructura Interna:
    - `_parse_core_work`: Transforma un objeto "work" de CORE en artículo estándar.
    - `search_core`: Función principal de búsqueda federada.

Entradas / Dependencias:
    - Librería `aiohttp`.
    - API Key de CORE configurada en `Settings`.

Salidas / Efectos:
    - Retorna una lista de artículos normalizados listos para su persistencia.
    - Requiere una clave de API válida para operar; de lo contrario, retorna lista vacía.

Ejemplo de Integración:
    articles = await search_core("hydroponics", max_results=20)
"""

import logging
from typing import Any

import aiohttp

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CORE_API = "https://api.core.ac.uk/v3"


def _parse_core_work(item: dict) -> dict[str, Any]:
    """
    Parsea un objeto de trabajo (work) de CORE al formato estándar de AgriSearch.

    Extrae DOI, título, autores, año, abstract y URL de descarga del PDF.

    Args:
        item (dict): Diccionario crudo retornado por la API de CORE.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Authors
    authors_raw = item.get("authors", [])
    if isinstance(authors_raw, list):
        authors = ", ".join(
            a.get("name", "") if isinstance(a, dict) else str(a)
            for a in authors_raw[:20]
        )
    else:
        authors = str(authors_raw)

    # Year from publishedDate
    year = None
    pub_date = item.get("publishedDate") or item.get("yearPublished")
    if pub_date:
        try:
            year = int(str(pub_date)[:4])
        except (ValueError, TypeError):
            pass

    # Keywords/topics
    topics = item.get("topics", []) or []
    keywords = []
    for t in topics[:10]:
        if isinstance(t, dict):
            keywords.append(t.get("display_name", "") or t.get("name", ""))
        elif isinstance(t, str):
            keywords.append(t)

    return {
        "doi": item.get("doi"),
        "title": item.get("title", "No Title"),
        "authors": authors,
        "year": year,
        "abstract": item.get("abstract"),
        "journal": item.get("publisher") or item.get("journals", [{}])[0].get("title") if item.get("journals") else None,
        "url": f"https://doi.org/{item['doi']}" if item.get("doi") else item.get("downloadUrl") or item.get("sourceFulltextUrls", [None])[0] if item.get("sourceFulltextUrls") else None,
        "keywords": ", ".join(keywords),
        "external_id": str(item.get("id", "")),
        "open_access_url": item.get("downloadUrl"),
    }


async def search_core(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos de acceso abierto en CORE que coincidan con la consulta.

    Args:
        query (str): Términos de búsqueda.
        max_results (int): Cantidad máxima de resultados.
        year_from (int | None): Año mínimo de publicación.
        year_to (int | None): Año máximo de publicación.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    if not settings.core_api_key:
        logger.warning("CORE API key not configured, skipping CORE search")
        return []

    articles: list[dict[str, Any]] = []

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "limit": min(max_results, 100),
            }
            if year_from:
                params["q"] += f" AND yearPublished>={year_from}"
            if year_to:
                params["q"] += f" AND yearPublished<={year_to}"

            headers = {"Authorization": f"Bearer {settings.core_api_key}"}

            async with session.get(
                f"{CORE_API}/search/works", params=params, headers=headers
            ) as resp:
                if resp.status != 200:
                    logger.warning("CORE API returned %d", resp.status)
                    return []

                data = await resp.json()
                results = data.get("results", [])

                for item in results:
                    parsed = _parse_core_work(item)
                    if parsed["title"] and parsed["title"] != "No Title":
                        articles.append(parsed)

        logger.info("CORE: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("CORE search failed: %s", str(e))

    return articles[:max_results]
