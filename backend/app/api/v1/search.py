"""
AgriSearch Backend - Search & Download API endpoints.

Endpoints for building queries, executing searches, listing articles, and downloading PDFs.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
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
from app.services.search_service import execute_search, get_project_articles, delete_search_query
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
        concepts=result.get("concepts", []),
        synonyms=result.get("synonyms", {}),
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
            raw_prompt=payload.raw_prompt,
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
        adapted_queries=result.get("adapted_queries", {}),
        prompt_used=payload.raw_prompt,
    )


@router.get(
    "/articles/{project_id}",
    summary="List articles for a project",
)
async def list_articles(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
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


@router.post(
    "/upload-pdf/{article_id}",
    response_model=ArticleResponse,
    summary="Manually upload a PDF for an article",
)
async def upload_pdf(
    article_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Manually upload a PDF and link it to the given article ID."""
    from sqlalchemy import select
    from app.models.project import Article, Project, SearchQuery, DownloadStatus
    from app.core.config import get_settings
    import shutil
    from pathlib import Path

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    project = await db.get(Project, article.project_id)
    
    sq_query = select(SearchQuery).where(SearchQuery.project_id == article.project_id).order_by(SearchQuery.created_at.asc())
    sq_result = await db.execute(sq_query)
    search_queries = list(sq_result.scalars().all())
    sq_map = {sq.id: f"Busqueda_{idx}" for idx, sq in enumerate(search_queries, 1)}
    search_name = sq_map.get(article.search_query_id, "Sin_Busqueda")

    settings = get_settings()
    pdf_dir = settings.get_project_pdfs_dir(article.project_id, project.name if project else None, search_name)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Use the provided filename but make it somewhat safe
    safe_filename = "".join([c if c.isalnum() or c in " ._-" else "_" for c in file.filename])
    file_path = pdf_dir / safe_filename

    # If file exists, prepend id to avoid overwrite, unless it's the exact same upload intent
    if file_path.exists():
        file_path = pdf_dir / f"{article.id[:8]}_{safe_filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error("Error saving manual upload %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail="No se pudo guardar el archivo.")

    article.local_pdf_path = str(file_path)
    article.download_status = DownloadStatus.SUCCESS
    await db.commit()
    await db.refresh(article)

    return ArticleResponse.model_validate(article)


@router.delete(
    "/{project_id}/{query_id}",
    summary="Delete a search query with its articles and PDFs",
)
async def delete_search_endpoint(
    project_id: str,
    query_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a search query and its associated articles and files."""
    try:
        await delete_search_query(db=db, project_id=project_id, query_id=query_id)
        return {"status": "success", "message": "Search query deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete search query: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to delete search query")
