"""
AgriSearch Backend - Pydantic schemas for API request/response validation.

Separated from SQLAlchemy models to maintain clean boundaries.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ──────────────────── Project Schemas ────────────────────


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Optional project description")
    agri_area: str = Field("general", description="Agricultural area focus")
    language: str = Field("es", description="Primary language (BCP-47)")


class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    id: str
    name: str
    description: str | None
    agri_area: str
    language: str
    created_at: datetime
    updated_at: datetime
    article_count: int = 0

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Schema for listing projects."""
    projects: list[ProjectResponse]
    total: int


# ──────────────────── Search Schemas ────────────────────


class SearchBuildQueryRequest(BaseModel):
    """Schema for requesting query generation from natural language."""
    user_input: str = Field(..., min_length=5, description="Natural language description of the research topic")
    agri_area: str = Field("general", description="Agricultural area for context")
    year_from: int | None = Field(None, description="Start year filter")
    year_to: int | None = Field(None, description="End year filter")
    language: str = Field("es", description="Language preference for query generation")


class GeneratedQuery(BaseModel):
    """Schema for a generated search query."""
    boolean_query: str = Field(..., description="Generated boolean/semantic query")
    suggested_terms: list[str] = Field(default_factory=list, description="Suggested AGROVOC/MeSH terms")
    pico_breakdown: dict[str, str] = Field(default_factory=dict, description="PICO/PEO breakdown")
    explanation: str = Field("", description="Explanation of the generated query")


class SearchQueryResponse(BaseModel):
    id: str
    project_id: str
    raw_input: str
    generated_query: str
    databases_used: str
    total_results: int
    duplicates_removed: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchExecuteRequest(BaseModel):
    """Schema for executing a search across databases."""
    project_id: str = Field(..., description="Project UUID")
    query: str = Field(..., description="Search query to execute")
    databases: list[str] = Field(
        default=["openalex", "semantic_scholar", "arxiv"],
        description="Databases to search",
    )
    max_results_per_source: int = Field(50, ge=10, le=500, description="Max results per DB")
    year_from: int | None = None
    year_to: int | None = None


class ArticleResponse(BaseModel):
    """Schema for an article in API responses."""
    id: str
    doi: str | None
    title: str
    authors: str | None
    year: int | None
    abstract: str | None
    journal: str | None
    url: str | None
    keywords: str | None
    source_database: str
    download_status: str
    is_duplicate: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResultsResponse(BaseModel):
    """Schema for search execution results."""
    project_id: str
    query_id: str
    total_found: int
    duplicates_removed: int
    articles: list[ArticleResponse]
    counts_by_source: dict[str, int]


# ──────────────────── Download Schemas ────────────────────


class DownloadRequest(BaseModel):
    """Schema for requesting article downloads."""
    project_id: str
    article_ids: list[str] | None = Field(None, description="Specific articles to download. None = all pending.")


class DownloadProgressResponse(BaseModel):
    """Schema for download progress updates."""
    total: int
    downloaded: int
    failed: int
    paywall: int
    in_progress: int
    articles: list[ArticleResponse] = []
