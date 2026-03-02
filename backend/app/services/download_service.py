"""
AgriSearch Backend - Download Service.

Handles downloading full-text PDFs for articles with open access URLs.
Includes rate limiting, DOI validation, and PDF verification.
"""

import asyncio
import logging
import re
from pathlib import Path

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.project import Article, DownloadStatus

logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiter semaphore
_download_semaphore = asyncio.Semaphore(settings.download_rate_limit)

PDF_MAGIC_BYTES = b"%PDF"


def _sanitize_filename(text: str) -> str:
    """Create a safe filename from arbitrary text."""
    safe = re.sub(r'[<>:"/\\|?*]', '_', text)
    safe = re.sub(r'\s+', '_', safe)
    return safe[:100]


async def _download_single_pdf(
    session: aiohttp.ClientSession,
    article: Article,
    pdf_dir: Path,
) -> tuple[str, str]:
    """
    Download a single PDF for an article.

    Returns (article_id, status) where status is one of the DownloadStatus values.
    """
    url = article.open_access_url
    if not url:
        return article.id, DownloadStatus.NOT_FOUND.value

    # Build filename
    first_author = (article.authors or "unknown").split(",")[0].strip().split()[-1]
    year = article.year or "nd"
    title_slug = _sanitize_filename(article.title)[:50]
    filename = f"{year}_{first_author}_{title_slug}.pdf"
    filepath = pdf_dir / filename

    # Skip if already downloaded
    if filepath.exists() and filepath.stat().st_size > 1000:
        return article.id, DownloadStatus.SUCCESS.value

    async with _download_semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=settings.download_timeout)) as resp:
                if resp.status == 403 or resp.status == 401:
                    return article.id, DownloadStatus.PAYWALL.value
                if resp.status != 200:
                    logger.warning("Download failed for %s: HTTP %d", article.doi, resp.status)
                    return article.id, DownloadStatus.FAILED.value

                content = await resp.read()

                # Validate it's actually a PDF
                if not content[:4].startswith(PDF_MAGIC_BYTES):
                    logger.warning("Downloaded file for %s is not a PDF", article.doi)
                    return article.id, DownloadStatus.FAILED.value

                filepath.write_bytes(content)
                logger.info("Downloaded: %s (%d bytes)", filename, len(content))
                return article.id, DownloadStatus.SUCCESS.value

        except asyncio.TimeoutError:
            logger.warning("Download timeout for %s", article.doi)
            return article.id, DownloadStatus.FAILED.value
        except Exception as e:
            logger.error("Download error for %s: %s", article.doi, str(e))
            return article.id, DownloadStatus.FAILED.value


async def download_articles(
    db: AsyncSession,
    project_id: str,
    article_ids: list[str] | None = None,
) -> dict:
    """
    Download PDFs for articles in a project.

    If article_ids is None, downloads all articles with status PENDING and an open_access_url.
    Returns a summary of download results.
    """
    # Build query
    query = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )

    if article_ids:
        query = query.where(Article.id.in_(article_ids))
    else:
        query = query.where(
            Article.download_status == DownloadStatus.PENDING,
            Article.open_access_url.isnot(None),
        )

    result = await db.execute(query)
    articles = list(result.scalars().all())

    if not articles:
        return {
            "total": 0,
            "downloaded": 0,
            "failed": 0,
            "paywall": 0,
        }

    from app.models.project import Project, SearchQuery
    project = await db.get(Project, project_id)
    
    sq_query = select(SearchQuery).where(SearchQuery.project_id == project_id).order_by(SearchQuery.created_at.asc())
    sq_result = await db.execute(sq_query)
    search_queries = list(sq_result.scalars().all())
    sq_map = {sq.id: f"Busqueda_{idx}" for idx, sq in enumerate(search_queries, 1)}

    logger.info("Starting download of %d articles for project %s", len(articles), project_id)

    # Download in parallel (bounded by semaphore)
    async with aiohttp.ClientSession(
        headers={"User-Agent": "AgriSearch/0.1 (Academic Research Tool)"}
    ) as session:
        tasks = []
        for article in articles:
            search_name = sq_map.get(article.search_query_id, "Sin_Busqueda")
            pdf_dir = settings.get_project_pdfs_dir(project_id, project.name if project else None, search_name)
            tasks.append(_download_single_pdf(session, article, pdf_dir))
        
        results = await asyncio.gather(*tasks)

    # Update DB with results
    status_counts = {"downloaded": 0, "failed": 0, "paywall": 0, "not_found": 0}
    article_map = {a.id: a for a in articles}

    for article_id, status in results:
        article = article_map.get(article_id)
        if not article:
            continue

        article.download_status = status
        if status == DownloadStatus.SUCCESS.value:
            first_author = (article.authors or "unknown").split(",")[0].strip().split()[-1]
            year = article.year or "nd"
            title_slug = _sanitize_filename(article.title)[:50]
            article.local_pdf_path = str(pdf_dir / f"{year}_{first_author}_{title_slug}.pdf")
            status_counts["downloaded"] += 1
        elif status == DownloadStatus.PAYWALL.value:
            status_counts["paywall"] += 1
        elif status == DownloadStatus.NOT_FOUND.value:
            status_counts["not_found"] += 1
        else:
            status_counts["failed"] += 1

    await db.flush()

    return {
        "total": len(articles),
        **status_counts,
    }
