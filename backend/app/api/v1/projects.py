"""
AgriSearch Backend - Project API endpoints.

CRUD operations for research projects (systematic reviews).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.project import Project, Article, SearchQuery, ScreeningSession
from app.models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse, SearchQueryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=201, summary="Create a new review project")
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new systematic review project with isolated data storage."""
    project = Project(
        name=payload.name,
        description=payload.description,
        agri_area=payload.agri_area,
        language=payload.language,
        llm_model=payload.llm_model,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    logger.info("Created project: %s (%s)", project.name, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        agri_area=project.agri_area,
        language=project.language,
        llm_model=project.llm_model,
        created_at=project.created_at,
        updated_at=project.updated_at,
        article_count=0,
    )


@router.get("/", response_model=ProjectListResponse, summary="List all projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    # Get projects with article counts and reviewed counts
    # Using scalar subqueries to avoid Cartesian product explosion
    article_count_subq = (
        select(func.count(Article.id))
        .where((Article.project_id == Project.id) & (Article.is_duplicate == False))
        .correlate(Project)
        .scalar_subquery()
    )
    
    reviewed_count_subq = (
        select(func.coalesce(func.sum(ScreeningSession.reviewed_count), 0))
        .where(ScreeningSession.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )

    query = (
        select(
            Project,
            article_count_subq.label("article_count"),
            reviewed_count_subq.label("reviewed_count"),
        )
        .order_by(Project.updated_at.desc())
    )

    result = await db.execute(query)
    rows = result.all()

    projects = [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            agri_area=p.agri_area,
            language=p.language,
            llm_model=p.llm_model,
            created_at=p.created_at,
            updated_at=p.updated_at,
            article_count=a_count or 0,
            reviewed_count=r_count or 0,
        )
        for p, a_count, r_count in rows
    ]

    return ProjectListResponse(projects=projects, total=len(projects))


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get a project by ID")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get details of a specific project including article count."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    count_query = select(func.count(Article.id)).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )
    count = (await db.execute(count_query)).scalar() or 0
    
    review_count_query = select(func.coalesce(func.sum(ScreeningSession.reviewed_count), 0)).where(
        ScreeningSession.project_id == project_id
    )
    r_count = (await db.execute(review_count_query)).scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        agri_area=project.agri_area,
        language=project.language,
        llm_model=project.llm_model,
        created_at=project.created_at,
        updated_at=project.updated_at,
        article_count=count,
        reviewed_count=r_count,
    )


@router.put("/{project_id}", response_model=ProjectResponse, summary="Update a project")
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update project metadata."""
    logger.info(f"Updating project {project_id} with payload: {payload.dict(exclude_unset=True)}")
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.agri_area is not None:
        project.agri_area = payload.agri_area
    if payload.language is not None:
        project.language = payload.language
    if payload.llm_model is not None:
        project.llm_model = payload.llm_model

    await db.commit()
    await db.refresh(project)

    # Get count for response
    count_query = select(func.count(Article.id)).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )
    count = (await db.execute(count_query)).scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        agri_area=project.agri_area,
        language=project.language,
        llm_model=project.llm_model,
        created_at=project.created_at,
        updated_at=project.updated_at,
        article_count=count,
    )


@router.delete("/{project_id}", status_code=204, summary="Delete a project")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a project and all its associated data."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    logger.info("Deleted project: %s", project_id)


@router.post("/{project_id}/open-folder", summary="Open the local PDF folder on the server")
async def open_project_folder(project_id: str, db: AsyncSession = Depends(get_db)):
    """Open the host OS file explorer at the project's PDF directory."""
    import os
    import subprocess
    from app.core.config import get_settings
    
    project = await db.get(Project, project_id)
    settings = get_settings()
    pdf_dir = settings.get_project_data_dir(project_id, project.name if project else None)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if os.name == 'nt': # Windows
            os.startfile(pdf_dir)
        elif os.name == 'posix':
            subprocess.Popen(['xdg-open', str(pdf_dir)])
        return {"status": "opened", "path": str(pdf_dir)}
    except Exception as e:
        logger.error("Failed to open folder: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/searches", response_model=list[SearchQueryResponse], summary="List searches for a project")
async def list_project_searches(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SearchQueryResponse]:
    """Get all executed searches within a project with their screening availability stats."""
    from app.models.project import Article, DownloadStatus, ScreeningDecision

    query = (
        select(SearchQuery)
        .where(SearchQuery.project_id == project_id)
        .order_by(SearchQuery.created_at.asc())
    )
    result = await db.execute(query)
    searches = result.scalars().all()
    
    responses = []
    
    for s in searches:
        # Get total downloaded
        stmt_dl = select(func.count(Article.id)).where(
            Article.search_query_id == s.id,
            Article.download_status == DownloadStatus.SUCCESS,
            Article.is_duplicate == False
        )
        total_dl = (await db.execute(stmt_dl)).scalar_one_or_none() or 0
        
        # Get assigned downloaded
        stmt_assigned = (
            select(func.count(func.distinct(ScreeningDecision.article_id)))
            .join(Article, ScreeningDecision.article_id == Article.id)
            .where(
                Article.search_query_id == s.id,
                Article.download_status == DownloadStatus.SUCCESS,
                Article.is_duplicate == False
            )
        )
        assigned = (await db.execute(stmt_assigned)).scalar_one_or_none() or 0
        
        resp = SearchQueryResponse.model_validate(s)
        resp.total_downloaded = total_dl
        resp.unassigned_articles = max(0, total_dl - assigned)
        responses.append(resp)
        
    return responses

