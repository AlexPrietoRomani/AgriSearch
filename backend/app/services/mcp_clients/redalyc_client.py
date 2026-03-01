"""
AgriSearch - Redalyc Client.

Searches Redalyc for open access scientific articles from Iberoamerica.
Requires free token from: https://redalyc.org
"""

import logging
from typing import Any

import aiohttp

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

REDALYC_API = "https://api.redalyc.org/v1"


def _parse_redalyc_work(item: dict) -> dict[str, Any]:
    """Parse a Redalyc result into our standard article format."""
    # Authors
    authors_raw = item.get("authors", [])
    if isinstance(authors_raw, list):
        authors = ", ".join(
            a.get("name", "") if isinstance(a, dict) else str(a)
            for a in authors_raw[:20]
        )
    else:
        authors = str(authors_raw)

    # Keywords
    keywords_raw = item.get("keywords", [])
    if isinstance(keywords_raw, list):
        keywords = ", ".join(str(k) for k in keywords_raw[:10])
    else:
        keywords = str(keywords_raw)

    return {
        "doi": item.get("doi"),
        "title": item.get("title", "No Title"),
        "authors": authors,
        "year": item.get("year"),
        "abstract": item.get("abstract"),
        "journal": item.get("journal") or item.get("source"),
        "url": item.get("url") or (f"https://doi.org/{item['doi']}" if item.get("doi") else None),
        "keywords": keywords,
        "external_id": item.get("id") or item.get("doi"),
        "open_access_url": item.get("pdf_url") or item.get("url"),
    }


async def search_redalyc(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Search Redalyc for articles matching the query.
    """
    if not settings.redalyc_token:
        logger.warning("Redalyc token not configured, skipping Redalyc search")
        return []

    articles: list[dict[str, Any]] = []

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "limit": min(max_results, 100),
            }
            if year_from:
                params["year_from"] = year_from
            if year_to:
                params["year_to"] = year_to

            headers = {"Authorization": f"Bearer {settings.redalyc_token}"}

            async with session.get(
                f"{REDALYC_API}/search", params=params, headers=headers
            ) as resp:
                if resp.status != 200:
                    logger.warning("Redalyc API returned %d", resp.status)
                    return []

                data = await resp.json()
                results = data.get("results", [])

                for item in results:
                    parsed = _parse_redalyc_work(item)
                    if parsed["title"] and parsed["title"] != "No Title":
                        articles.append(parsed)

        logger.info("Redalyc: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("Redalyc search failed: %s", str(e))

    return articles[:max_results]
