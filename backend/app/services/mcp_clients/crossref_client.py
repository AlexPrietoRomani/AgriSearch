"""
Archivo: crossref_client.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Cliente para la API de Crossref (https://www.crossref.org). 
Permite la búsqueda de metadatos bibliográficos de artículos científicos a través de su DOI 
o por términos de búsqueda. Es fundamental para la identificación de fuentes formales.

Acciones Principales:
    - Ejecuta búsquedas utilizando la librería `habanero`.
    - Normaliza la respuesta de Crossref (JSON) al formato estándar de AgriSearch.
    - Limpia etiquetas HTML de los abstracts si están presentes.

Estructura Interna:
    - `_parse_crossref_work`: Parsea un objeto "work" de Crossref.
    - `search_crossref`: Ejecuta la búsqueda de forma asíncrona (usando `run_in_executor` para `habanero`).

Entradas / Dependencias:
    - Librería `habanero`.
    - Configuración de correo para el "polite pool" de Crossref.

Ejemplo de Integración:
    articles = await search_crossref("soil health", max_results=15)
"""

import logging
from typing import Any

from habanero import Crossref

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_crossref_work(work: dict) -> dict[str, Any]:
    """
    Parsea un objeto de trabajo (work) de Crossref al formato estándar de AgriSearch.

    Extrae DOI, título, autores, año, abstract (limpiando HTML) y revista.

    Args:
        work (dict): Diccionario crudo retornado por habanero/Crossref.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Authors
    authors_list = []
    for author in work.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors_list.append(name)

    # Year
    year = None
    for date_field in ["published-print", "published-online", "created"]:
        date_parts = work.get(date_field, {}).get("date-parts", [[None]])
        if date_parts and date_parts[0] and date_parts[0][0]:
            year = date_parts[0][0]
            break

    # Abstract (Crossref may include HTML tags)
    abstract = work.get("abstract", "")
    if abstract:
        # Strip simple HTML tags
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract).strip()

    return {
        "doi": work.get("DOI"),
        "title": work.get("title", [None])[0] if work.get("title") else "No Title",
        "authors": ", ".join(authors_list[:20]),
        "year": year,
        "abstract": abstract or None,
        "journal": work.get("container-title", [None])[0] if work.get("container-title") else None,
        "url": f"https://doi.org/{work.get('DOI')}" if work.get("DOI") else None,
        "keywords": ", ".join(work.get("subject", [])[:10]),
        "external_id": work.get("DOI"),
        "open_access_url": None,
    }


async def search_crossref(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos en Crossref que coincidan con la consulta.

    Utiliza `habanero` de forma sincrónica, envuelto en un ejecutor para compatibilidad asíncrona.

    Args:
        query (str): Términos de búsqueda.
        max_results (int): Cantidad máxima de resultados.
        year_from (int | None): Año mínimo de publicación.
        year_to (int | None): Año máximo de publicación.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    import asyncio

    def _sync_search():
        cr = Crossref(mailto=settings.crossref_mailto)
        filters = {}
        if year_from:
            filters["from-pub-date"] = f"{year_from}"
        if year_to:
            filters["until-pub-date"] = f"{year_to}"

        try:
            result = cr.works(
                query=query,
                limit=min(max_results, 100),
                filter=filters if filters else None,
            )
            items = result.get("message", {}).get("items", [])
            articles = []
            for item in items:
                parsed = _parse_crossref_work(item)
                if parsed["title"] and parsed["title"] != "No Title":
                    articles.append(parsed)
            return articles[:max_results]
        except Exception as e:
            logger.error("Crossref search failed: %s", str(e))
            return []

    articles = await asyncio.get_event_loop().run_in_executor(None, _sync_search)
    logger.info("Crossref: found %d articles for query: %s", len(articles), query[:60])
    return articles
