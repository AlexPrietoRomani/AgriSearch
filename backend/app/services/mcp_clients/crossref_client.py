"""
AgriSearch - Crossref Client.

Searches Crossref for scientific articles using the habanero library.
Free API, no key required. Email recommended for polite pool.
"""

import logging
from typing import Any

from habanero import Crossref

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_crossref_work(work: dict) -> dict[str, Any]:
    """Parse a Crossref work into our standard article format."""
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
    Search Crossref for articles matching the query.

    Uses habanero (synchronous) wrapped for async compatibility.
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
