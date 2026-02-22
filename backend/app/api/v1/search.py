"""
AgriSearch Backend - Search & Download API endpoints.

Endpoints for building queries, executing searches, listing articles, and downloading PDFs.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.schemas import (
    ArticleResponse,
    DownloadProgressResponse,
    DownloadRequest,
    GeneratedQuery,
    SearchBuildQueryRequest,
    SearchExecuteRequest,
    SearchResultsResponse,
)
from app.services.llm_service import generate_search_query
from app.services.search_service import execute_search, get_project_articles
from app.services.download_service import download_articles

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "/build-query",
    response_model=GeneratedQuery,
    summary="Generate a search query from natural language",
)
async def build_query(payload: SearchBuildQueryRequest) -> GeneratedQuery:
    """
    Use the LLM to transform a natural language research question
    into an optimized boolean search query with AGROVOC terms and PICO breakdown.
    """
    result = await generate_search_query(
        user_input=payload.user_input,
        agri_area=payload.agri_area,
        language=payload.language,
        year_from=payload.year_from,
        year_to=payload.year_to,
    )

    return GeneratedQuery(
        boolean_query=result.get("boolean_query", payload.user_input),
        suggested_terms=result.get("suggested_terms", []),
        pico_breakdown=result.get("pico_breakdown", {}),
        explanation=result.get("explanation", ""),
    )


@router.post(
    "/execute",
    response_model=SearchResultsResponse,
    summary="Execute search across scientific databases",
)
async def execute_search_endpoint(
    payload: SearchExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResultsResponse:
    """
    Execute the search query across selected databases (OpenAlex, Semantic Scholar, ArXiv).
    Deduplicates by DOI and fuzzy title matching. Stores results in the project database.
    """
    try:
        result = await execute_search(
            db=db,
            project_id=payload.project_id,
            query=payload.query,
            databases=payload.databases,
            max_results_per_source=payload.max_results_per_source,
            year_from=payload.year_from,
            year_to=payload.year_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Search execution failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    articles = [
        ArticleResponse.model_validate(a) for a in result["articles"]
    ]

    return SearchResultsResponse(
        project_id=payload.project_id,
        query_id=result["query_id"],
        total_found=result["total_found"],
        duplicates_removed=result["duplicates_removed"],
        articles=articles,
        counts_by_source=result["counts_by_source"],
    )


@router.get(
    "/articles/{project_id}",
    summary="List articles for a project",
)
async def list_articles(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    download_status: str | None = Query(None),
    search_query_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get paginated articles for a project, optionally filtered by download status or search query id."""
    articles, total = await get_project_articles(
        db=db,
        project_id=project_id,
        skip=skip,
        limit=limit,
        download_status=download_status,
        search_query_id=search_query_id,
    )

    return {
        "articles": [ArticleResponse.model_validate(a) for a in articles],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post(
    "/download",
    response_model=DownloadProgressResponse,
    summary="Download PDFs for articles",
)
async def download_pdfs(
    payload: DownloadRequest,
    db: AsyncSession = Depends(get_db),
) -> DownloadProgressResponse:
    """
    Download open access PDFs for articles in a project.
    If article_ids is not provided, downloads all pending articles with OA URLs.
    """
    try:
        result = await download_articles(
            db=db,
            project_id=payload.project_id,
            article_ids=payload.article_ids,
        )
    except Exception as e:
        logger.error("Download failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

    return DownloadProgressResponse(
        total=result["total"],
        downloaded=result.get("downloaded", 0),
        failed=result.get("failed", 0),
        paywall=result.get("paywall", 0),
        in_progress=0,
    )
