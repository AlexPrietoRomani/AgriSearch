"""
AgriSearch - Semantic Scholar Client.

Searches Semantic Scholar for scientific articles via the public API.
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SS_API = "https://api.semanticscholar.org/graph/v1"
SS_FIELDS = "paperId,externalIds,title,authors,year,abstract,venue,url,openAccessPdf,publicationTypes"


def _parse_ss_paper(paper: dict) -> dict[str, Any]:
    """Parse a Semantic Scholar paper into our standard article format."""
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
    }


async def search_semantic_scholar(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Search Semantic Scholar for articles matching the query.

    Returns a list of normalized article dictionaries.
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
                url = (
                    f"{SS_API}/paper/search"
                    f"?query={query}"
                    f"&limit={limit}"
                    f"&offset={offset}"
                    f"&fields={SS_FIELDS}"
                    f"{year_filter}"
                )

                async with session.get(url) as resp:
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
