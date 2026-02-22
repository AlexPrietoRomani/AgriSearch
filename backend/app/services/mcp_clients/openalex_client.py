"""
AgriSearch - OpenAlex MCP Client.

Searches OpenAlex for scientific articles.
Uses the OpenAlex REST API directly (no MCP dependency at runtime).
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
MAILTO = "agrisearch@example.com"


def _parse_authors(authorships: list[dict]) -> str:
    """Extract author names from OpenAlex authorships."""
    names = []
    for auth in authorships[:20]:  # Limit to 20 authors
        display_name = auth.get("author", {}).get("display_name", "")
        if display_name:
            names.append(display_name)
    return ", ".join(names)


def _parse_openalex_work(work: dict) -> dict[str, Any]:
    """Parse an OpenAlex work into our standard article format."""
    # Extract OA URL
    oa_url = None
    best_oa = work.get("best_oa_location")
    if best_oa:
        oa_url = best_oa.get("pdf_url") or best_oa.get("landing_page_url")

    # Extract keywords
    keywords_list = []
    for kw in work.get("keywords", []):
        if isinstance(kw, dict):
            keywords_list.append(kw.get("display_name", ""))
        elif isinstance(kw, str):
            keywords_list.append(kw)

    return {
        "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
        "title": work.get("title", "No Title"),
        "authors": _parse_authors(work.get("authorships", [])),
        "year": work.get("publication_year"),
        "abstract": work.get("abstract") or _reconstruct_abstract(work.get("abstract_inverted_index")),
        "journal": work.get("primary_location", {}).get("source", {}).get("display_name") if work.get("primary_location") else None,
        "url": work.get("doi") or work.get("id"),
        "keywords": ", ".join(keywords_list[:10]),
        "external_id": work.get("id"),
        "open_access_url": oa_url,
    }


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index format."""
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
    Search OpenAlex for articles matching the query.

    Returns a list of normalized article dictionaries.
    """
    articles: list[dict[str, Any]] = []
    per_page = min(max_results, 50)
    pages_needed = (max_results + per_page - 1) // per_page

    # Build filter
    filters = []
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
                    "select": "id,doi,title,authorships,publication_year,abstract_inverted_index,primary_location,keywords,best_oa_location,abstract",
                }
                if filters:
                    params["filter"] = ",".join(filters)

                async with session.get(f"{OPENALEX_API}/works", params=params) as resp:
                    if resp.status != 200:
                        logger.warning("OpenAlex API returned %d on page %d", resp.status, page)
                        break

                    data = await resp.json()
                    works = data.get("results", [])

                    if not works:
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
