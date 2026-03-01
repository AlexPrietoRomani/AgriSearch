"""
AgriSearch - SciELO Client.

Searches SciELO for scientific articles from Latin America and the Caribbean.
Free API, no key required.
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SCIELO_SEARCH_API = "https://search.scielo.org"


def _parse_scielo_work(item: dict) -> dict[str, Any]:
    """Parse a SciELO search result into our standard article format."""
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
    }


async def search_scielo(
    query: str,
    max_results: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """
    Search SciELO for articles matching the query.
    Uses the SciELO search API with JSON output.
    """
    articles: list[dict[str, Any]] = []

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "output": "json",
                "count": min(max_results, 100),
                "from": 0,
                "lang": "en",
            }
            if year_from:
                params["filter[year_cluster][]"] = f"{year_from}-{year_to or 2030}"

            async with session.get(
                f"{SCIELO_SEARCH_API}/", params=params
            ) as resp:
                if resp.status != 200:
                    logger.warning("SciELO API returned %d", resp.status)
                    return []

                # SciELO can return HTML sometimes, try JSON
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    data = await resp.json()
                else:
                    # Try parsing as JSON anyway
                    text = await resp.text()
                    import json
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning("SciELO returned non-JSON response")
                        return []

                docs = data.get("response", {}).get("docs", [])

                for doc in docs:
                    parsed = _parse_scielo_work(doc)
                    if parsed["title"] and parsed["title"] != "No Title":
                        articles.append(parsed)

        logger.info("SciELO: found %d articles for query: %s", len(articles), query[:60])

    except Exception as e:
        logger.error("SciELO search failed: %s", str(e))

    return articles[:max_results]
