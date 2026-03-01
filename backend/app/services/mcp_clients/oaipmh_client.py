"""
AgriSearch - OAI-PMH Client.

Generic OAI-PMH harvester for AgEcon Search and Organic Eprints.
Both use the OAI-PMH protocol (free, no key required).

Endpoints:
  - AgEcon Search: http://ageconsearch.umn.edu/oai2d
  - Organic Eprints: http://orgprints.org/cgi/oai2
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
    """Parse OAI-PMH Dublin Core metadata into our standard article format."""
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
    Harvest records from an OAI-PMH endpoint and filter by query terms.

    OAI-PMH doesn't support full-text search natively, so we harvest
    recent records and filter locally by matching query terms in title/abstract.

    Args:
        source: "agecon" or "organic_eprints"
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
