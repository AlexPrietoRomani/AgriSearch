"""
AgriSearch Backend - Search Service.

Orchestrates searching across multiple scientific databases (OpenAlex, Semantic Scholar, ArXiv),
consolidates results, and removes duplicates. All results are scoped by project_id.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone

from rapidfuzz import fuzz
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.project import Article, SearchQuery, Project
from app.services.mcp_clients.openalex_client import search_openalex
from app.services.mcp_clients.semantic_scholar_client import search_semantic_scholar
from app.services.mcp_clients.arxiv_client import search_arxiv
from app.services.llm_service import adapt_query_for_database

logger = logging.getLogger(__name__)
settings = get_settings()

DOI_REGEX = re.compile(r"^10\.\d{4,}/\S+$")


def _normalize_doi(doi: str | None) -> str | None:
    """Normalize a DOI for comparison."""
    if not doi:
        return None
    doi = doi.strip().lower()
    # Remove common prefixes
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi if DOI_REGEX.match(doi) else None


def _is_duplicate_title(title_a: str, title_b: str, threshold: float = 0.85) -> bool:
    """Check if two titles are fuzzy duplicates."""
    if not title_a or not title_b:
        return False
    ratio = fuzz.ratio(title_a.lower().strip(), title_b.lower().strip()) / 100.0
    return ratio >= threshold


async def execute_search(
    db: AsyncSession,
    project_id: str,
    query: str,
    databases: list[str],
    max_results_per_source: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """
    Execute a search across selected databases, deduplicate, and store results.

    Returns a summary of the search results including counts by source.
    """
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Store the search query
    search_query = SearchQuery(
        project_id=project_id,
        raw_input=query,
        generated_query=query,
        databases_used=",".join(databases),
    )
    db.add(search_query)
    await db.flush()

    # Adapt queries for each target DB concurrently
    adapt_tasks = []
    if "openalex" in databases: adapt_tasks.append(("openalex", adapt_query_for_database(query, "openalex")))
    if "semantic_scholar" in databases: adapt_tasks.append(("semantic_scholar", adapt_query_for_database(query, "semantic_scholar")))
    if "arxiv" in databases: adapt_tasks.append(("arxiv", adapt_query_for_database(query, "arxiv")))

    adapted_results = await asyncio.gather(*[t[1] for t in adapt_tasks], return_exceptions=True)
    adapted_queries = {}
    for (source_name, _), result in zip(adapt_tasks, adapted_results):
        if isinstance(result, Exception):
            logger.warning("Failed to adapt query for %s, using original. Error: %s", source_name, str(result))
            adapted_queries[source_name] = query
        else:
            adapted_queries[source_name] = result

    # Execute searches in parallel using adapted queries
    tasks = []
    if "openalex" in databases:
        tasks.append(("openalex", search_openalex(adapted_queries["openalex"], max_results_per_source, year_from, year_to)))
    if "semantic_scholar" in databases:
        tasks.append(("semantic_scholar", search_semantic_scholar(adapted_queries["semantic_scholar"], max_results_per_source, year_from, year_to)))
    if "arxiv" in databases:
        tasks.append(("arxiv", search_arxiv(adapted_queries["arxiv"], max_results_per_source, year_from, year_to)))

    all_articles: list[dict] = []
    counts_by_source: dict[str, int] = {}

    results = await asyncio.gather(
        *[t[1] for t in tasks],
        return_exceptions=True,
    )

    for (source_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error("Search failed for %s: %s", source_name, str(result))
            counts_by_source[source_name] = 0
            continue
        counts_by_source[source_name] = len(result)
        for article_data in result:
            article_data["source_database"] = source_name
            all_articles.append(article_data)

    logger.info(
        "Raw results: %s total from %s sources",
        len(all_articles),
        counts_by_source,
    )

    # ── Deduplication ──
    # First pass: deduplicate by normalized DOI
    seen_dois: dict[str, int] = {}
    unique_articles: list[dict] = []
    duplicates_removed = 0

    for article_data in all_articles:
        normalized_doi = _normalize_doi(article_data.get("doi"))
        if normalized_doi and normalized_doi in seen_dois:
            duplicates_removed += 1
            continue
        if normalized_doi:
            seen_dois[normalized_doi] = len(unique_articles)
        unique_articles.append(article_data)

    # Second pass: fuzzy title dedup for articles without DOI
    final_articles: list[dict] = []
    existing_titles: list[str] = []

    for article_data in unique_articles:
        title = article_data.get("title", "")
        is_dup = False
        for existing_title in existing_titles:
            if _is_duplicate_title(title, existing_title, settings.search_dedup_threshold):
                is_dup = True
                duplicates_removed += 1
                break
        if not is_dup:
            final_articles.append(article_data)
            existing_titles.append(title)

    # Also check against existing articles in the project
    existing_query = select(Article.doi, Article.title).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )
    existing_result = await db.execute(existing_query)
    existing_rows = existing_result.all()
    existing_project_dois = {_normalize_doi(r.doi) for r in existing_rows if r.doi}
    existing_project_titles = [r.title for r in existing_rows if r.title]

    new_articles: list[dict] = []
    for article_data in final_articles:
        normalized_doi = _normalize_doi(article_data.get("doi"))
        if normalized_doi and normalized_doi in existing_project_dois:
            duplicates_removed += 1
            continue
        title = article_data.get("title", "")
        is_dup = False
        for et in existing_project_titles:
            if _is_duplicate_title(title, et, settings.search_dedup_threshold):
                is_dup = True
                duplicates_removed += 1
                break
        if not is_dup:
            new_articles.append(article_data)

    # ── Store in DB ──
    stored_articles: list[Article] = []
    for article_data in new_articles:
        article = Article(
            project_id=project_id,
            search_query_id=search_query.id,
            doi=article_data.get("doi"),
            title=article_data.get("title", "Unknown Title"),
            authors=article_data.get("authors"),
            year=article_data.get("year"),
            abstract=article_data.get("abstract"),
            journal=article_data.get("journal"),
            url=article_data.get("url"),
            keywords=article_data.get("keywords"),
            source_database=article_data.get("source_database", "unknown"),
            external_id=article_data.get("external_id"),
            open_access_url=article_data.get("open_access_url"),
        )
        db.add(article)
        stored_articles.append(article)

    # Update search query stats
    search_query.total_results = len(new_articles)
    search_query.duplicates_removed = duplicates_removed

    await db.flush()

    logger.info(
        "Search complete: %d new articles stored, %d duplicates removed for project %s",
        len(new_articles),
        duplicates_removed,
        project_id,
    )

    return {
        "query_id": search_query.id,
        "total_found": len(new_articles),
        "duplicates_removed": duplicates_removed,
        "articles": stored_articles,
        "counts_by_source": counts_by_source,
    }


async def get_project_articles(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 50,
    download_status: str | None = None,
    search_query_id: str | None = None,
) -> tuple[list[Article], int]:
    """Get paginated articles for a project, optionally filtered by download status or search query id."""
    base_query = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )

    if download_status:
        base_query = base_query.where(Article.download_status == download_status)
    
    if search_query_id:
        base_query = base_query.where(Article.search_query_id == search_query_id)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated articles
    articles_query = base_query.order_by(Article.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(articles_query)
    articles = list(result.scalars().all())

    return articles, total
