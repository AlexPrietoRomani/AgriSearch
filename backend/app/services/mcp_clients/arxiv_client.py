"""
Archivo: arxiv_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente para la API de ArXiv (http://export.arxiv.org). 
Permite la búsqueda de artículos científicos (pre-prints) especializados en física, 
matemáticas y ciencias de la computación, con relevancia para la agricultura (ej. IA, sensores).

Acciones Principales:
    - Ejecuta consultas asíncronas a la API de ArXiv.
    - Parsea respuestas en formato Atom (XML) al formato estándar de AgriSearch.
    - Implementa filtrado por fecha (enviado a la API y post-hoc).

Estructura Interna:
    - `_parse_arxiv_entry`: Convierte una entrada Atom XML en artículo normalizado.
    - `search_arxiv`: Función principal para ejecutar la búsqueda federada.

Entradas / Dependencias:
    - Librería `aiohttp` para peticiones asíncronas.
    - Librería `xml.etree.ElementTree` para el parseo de XML.

Salidas / Efectos:
    - Retorna una lista de artículos normalizados con DOIs fabricados (`10.48550/arXiv...`).
    - Realiza llamadas de red asíncronas a export.arxiv.org.

Ejemplo de Integración:
    articles = await search_arxiv("precision agriculture", max_results=10)
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    """
    Parsea una entrada Atom de ArXiv al formato estándar de artículo de AgriSearch.

    Extrae el ID de ArXiv, DOI (si existe), autores, año, categorías y URL del PDF.

    Args:
        entry (ET.Element): Elemento XML de la entrada de ArXiv.

    Returns:
        dict[str, Any]: Diccionario con los metadatos normalizados del artículo.
    """
    # Extract ID and DOI
    arxiv_id = entry.findtext("atom:id", "", NS).split("/abs/")[-1]
    arxiv_id_match = arxiv_id.split('v')[0] if arxiv_id else None
    
    doi_elem = entry.find("atom:doi", NS)
    doi = doi_elem.text if doi_elem is not None else None
    
    if not doi and arxiv_id_match:
        doi = f"10.48550/arXiv.{arxiv_id_match}"

    # Extract authors
    authors = ", ".join(
        a.findtext("atom:name", "", NS)
        for a in entry.findall("atom:author", NS)
    )

    # Extract year from published date
    published = entry.findtext("atom:published", "", NS)
    year = int(published[:4]) if published else None

    # Extract categories as keywords
    categories = [
        c.get("term", "")
        for c in entry.findall("atom:category", NS)
    ]

    # Build PDF URL
    pdf_url = None
    for link in entry.findall("atom:link", NS):
        if link.get("title") == "pdf" or (link.get("type") == "application/pdf"):
            pdf_url = link.get("href")
            break
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return {
        "doi": doi,
        "title": entry.findtext("atom:title", "No Title", NS).strip().replace("\n", " "),
        "authors": authors,
        "year": year,
        "abstract": entry.findtext("atom:summary", "", NS).strip().replace("\n", " "),
        "journal": "arXiv",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "keywords": ", ".join(categories),
        "external_id": arxiv_id,
        "open_access_url": pdf_url,
        "document_type": "preprint",  # ArXiv es exclusivamente preprints
    }


async def search_arxiv(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Busca artículos en ArXiv que coincidan con la consulta.

    Construye la URL manualmente para evitar que aiohttp re-encodee el operador
    de rango de fecha `[YYYY+TO+YYYY]` que requiere el signo `+` literal en el
    parámetro `search_query`. El filtro de fecha se añade solo si no viene ya
    incluído en la query booleana (detectable por la presencia de `submittedDate`).

    Args:
        query (str): Consulta booleana con prefijos `all:`, `ti:`, etc.
        max_results (int): Máximo de resultados a retornar.
        year_from (int | None): Año de inicio del filtro.
        year_to (int | None): Año final del filtro.

    Returns:
        list[dict[str, Any]]: Lista de artículos normalizados.
    """
    import urllib.parse

    articles: list[dict[str, Any]] = []

    # Normaliza la query: si viene sin prefijo de campo, añade `all:`
    if not any(p in query for p in ("all:", "ti:", "au:", "abs:", "submittedDate")):
        search_query = f"all:{query}"
    else:
        search_query = query

    # Añade el rango de fecha SOLO si no viene ya en la query y si se especifica
    # El operador + debe ir literal (no codificado como %2B) en la URL de ArXiv
    if (year_from or year_to) and "submittedDate" not in search_query:
        start_date = f"{year_from or 2000}01010000"
        end_date = f"{year_to or 2030}12312359"
        # No usar urllib.parse.urlencode aqui porque el + debe ser literal
        search_query += f" AND submittedDate:[{start_date}+TO+{end_date}]"

    # Construye la URL manualmente para que el + del rango no sea re-codeado por aiohttp
    encoded_query = urllib.parse.quote(search_query, safe="+:()\"")
    url = (
        f"{ARXIV_API}"
        f"?search_query={encoded_query}"
        f"&start=0"
        f"&max_results={max_results}"
        f"&sortBy=relevance"
        f"&sortOrder=descending"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning("ArXiv API returned %d", resp.status)
                    return []

                xml_text = await resp.text()
                root = ET.fromstring(xml_text)

                entries = root.findall("atom:entry", NS)
                if not entries:
                    logger.warning(
                        "ArXiv: No entries found for search_query: %s. ResponseStatus: %d. Body: %s",
                        search_query, resp.status, xml_text[:500],
                    )

                for entry in entries:
                    parsed = _parse_arxiv_entry(entry)

                    # Validación post-hoc del año (refuerza el filtro nativo)
                    if year_from and parsed.get("year") and parsed["year"] < year_from:
                        continue
                    if year_to and parsed.get("year") and parsed["year"] > year_to:
                        continue

                    if parsed["title"] and parsed["title"] != "No Title":
                        articles.append(parsed)

                    if len(articles) >= max_results:
                        break

        logger.info("ArXiv: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("ArXiv search failed: %s", str(e))
        raise

    return articles[:max_results]
