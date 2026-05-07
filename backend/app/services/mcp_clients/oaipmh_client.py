"""
Archivo: oaipmh_client.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Recolector (harvester) genérico de OAI-PMH para fuentes como AgEcon Search y Organic Eprints.
Utiliza el protocolo OAI-PMH para obtener metadatos bibliográficos en formato Dublin Core.

Acciones Principales:
    - Realiza el "harvesting" de registros desde endpoints OAI-PMH conocidos.
    - Filtra los resultados localmente mediante la coincidencia de términos de búsqueda.
    - Normaliza los metadatos Dublin Core al formato estándar de AgriSearch.

Estructura Interna:
    - `_parse_oai_record`: Transforma los metadatos Dublin Core en el esquema de artículo interno.
    - `search_oaipmh`: Función principal que gestiona la conexión asíncrona y el filtrado local.

Entradas / Dependencias:
    - Librería `sickle` para la gestión del protocolo OAI-PMH.
    - Diccionario `OAI_ENDPOINTS` con las rutas de los repositorios soportados.

Ejemplo de Integración:
    articles = await search_oaipmh("organic farming", source="organic_eprints")
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Known OAI-PMH endpoints
OAI_ENDPOINTS = {
    "agecon": "http://ageconsearch.umn.edu/oai2d",
    "organic_eprints": "http://orgprints.org/cgi/oai2",
}


def _parse_oai_record(metadata: dict) -> dict[str, Any]:
    """
    Parsea los metadatos Dublin Core de un registro OAI-PMH al formato estándar de AgriSearch.

    Extrae título, autores (creadores), año, abstract (descripción) y DOIs/URLs.

    Args:
        metadata (dict): Diccionario con los campos Dublin Core extraídos por sickle.

    Returns:
        dict[str, Any]: Metadatos normalizados del artículo.
    """
    # Title
    title_raw = metadata.get("title", [])
    title = title_raw[0] if title_raw else "No Title"

    # Authors (dc:creator)
    creators = metadata.get("creator", [])
    authors = ", ".join(creators[:20]) if isinstance(creators, list) else str(creators)

    # Year from dc:date
    year = None
    dates = metadata.get("date", [])
    if dates:
        date_str = dates[0] if isinstance(dates, list) else str(dates)
        try:
            year = int(str(date_str)[:4])
        except (ValueError, TypeError):
            pass

    # Abstract from dc:description
    desc = metadata.get("description", [])
    abstract = desc[0] if desc and isinstance(desc, list) else (str(desc) if desc else None)

    # Keywords from dc:subject
    subjects = metadata.get("subject", [])
    if isinstance(subjects, list):
        keywords = ", ".join(subjects[:10])
    else:
        keywords = str(subjects)

    # DOI from dc:identifier (look for DOI patterns)
    doi = None
    identifiers = metadata.get("identifier", [])
    if isinstance(identifiers, list):
        for ident in identifiers:
            if isinstance(ident, str) and "doi.org" in ident:
                doi = ident.replace("https://doi.org/", "").replace("http://doi.org/", "")
                break

    # URL from dc:identifier (first URL)
    url = None
    if isinstance(identifiers, list):
        for ident in identifiers:
            if isinstance(ident, str) and ident.startswith("http"):
                url = ident
                break

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": abstract,
        "journal": None,  # OAI-PMH DC doesn't have a direct journal field
        "url": url,
        "keywords": keywords,
        "external_id": identifiers[0] if identifiers else None,
        "open_access_url": url,
    }


async def search_oaipmh(
    query: str,
    source: str = "agecon",
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Recolecta y filtra registros desde un endpoint OAI-PMH.

    Dado que OAI-PMH no soporta búsqueda por términos de forma nativa, esta función
    recolecta los registros recientes y aplica un filtro local de palabras clave.

    Args:
        query (str): Términos de búsqueda para el filtrado local.
        source (str): Identificador de la fuente ("agecon" o "organic_eprints").
        max_results (int): Cantidad máxima de resultados deseados.
        year_from (int | None): Año de inicio para la recolección.
        year_to (int | None): Año final para la recolección.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados que coinciden con la consulta.
    """
    import asyncio

    endpoint = OAI_ENDPOINTS.get(source)
    if not endpoint:
        logger.warning("Unknown OAI-PMH source: %s", source)
        return []

    def _sync_harvest():
        try:
            from sickle import Sickle
            sickle = Sickle(endpoint, max_retries=2, timeout=30)

            # Build date range params
            kwargs = {"metadataPrefix": "oai_dc"}
            if year_from:
                kwargs["from_"] = f"{year_from}-01-01"
            if year_to:
                kwargs["until"] = f"{year_to}-12-31"

            records = sickle.ListRecords(**kwargs)

            # Query terms for local filtering
            query_terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]

            articles = []
            count = 0
            max_scan = max_results * 10  # Scan up to 10x to find matching records

            for record in records:
                if count >= max_scan or len(articles) >= max_results:
                    break
                count += 1

                if not record.metadata:
                    continue

                parsed = _parse_oai_record(record.metadata)

                # Filter: at least one query term must appear in title or abstract
                searchable = f"{parsed.get('title', '')} {parsed.get('abstract', '')}".lower()
                if any(term in searchable for term in query_terms):
                    if parsed["title"] and parsed["title"] != "No Title":
                        articles.append(parsed)

            return articles

        except Exception as e:
            logger.error("OAI-PMH harvest failed for %s: %s", source, str(e))
            return []

    articles = await asyncio.get_event_loop().run_in_executor(None, _sync_harvest)
    logger.info("OAI-PMH (%s): found %d articles for query: %s", source, len(articles), query[:60])
    return articles[:max_results]
