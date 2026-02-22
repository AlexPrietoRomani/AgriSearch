"""
AgriSearch - ArXiv Client.

Searches ArXiv for scientific articles via the ArXiv API.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    """Parse an ArXiv Atom entry into our standard article format."""
    # Extract ID and DOI
    arxiv_id = entry.findtext("atom:id", "", NS).split("/abs/")[-1]
    doi_elem = entry.find("atom:doi", NS)
    doi = doi_elem.text if doi_elem is not None else None

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
    }


async def search_arxiv(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Search ArXiv for articles matching the query.

    ArXiv doesn't support native year filtering, so we filter post-hoc.
    Returns a list of normalized article dictionaries.
    """
    articles: list[dict[str, Any]] = []

    # Fetch more results than needed if year-filtering is active
    fetch_limit = max_results * 3 if (year_from or year_to) else max_results

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(fetch_limit, 300),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            async with session.get(ARXIV_API, params=params) as resp:
                if resp.status != 200:
                    logger.warning("ArXiv API returned %d", resp.status)
                    return []

                xml_text = await resp.text()
                root = ET.fromstring(xml_text)

                for entry in root.findall("atom:entry", NS):
                    parsed = _parse_arxiv_entry(entry)

                    # Year filter
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
