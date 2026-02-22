"""
AgriSearch Backend - Project API endpoints.

CRUD operations for research projects (systematic reviews).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.project import Project, Article
from app.models.schemas import ProjectCreate, ProjectResponse, ProjectListResponse

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
        created_at=project.created_at,
        updated_at=project.updated_at,
        article_count=0,
    )


@router.get("/", response_model=ProjectListResponse, summary="List all projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """List all systematic review projects with article counts."""
    # Get projects with article counts
    query = (
        select(
            Project,
            func.count(Article.id).label("article_count"),
        )
        .outerjoin(Article, (Article.project_id == Project.id) & (Article.is_duplicate == False))  # noqa: E712
        .group_by(Project.id)
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
            created_at=p.created_at,
            updated_at=p.updated_at,
            article_count=count,
        )
        for p, count in rows
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

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        agri_area=project.agri_area,
        language=project.language,
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
