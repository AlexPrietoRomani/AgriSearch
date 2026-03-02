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
    llm_model: str | None = Field(None, description="Preferred LLM model for this project")


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    agri_area: str | None = Field(None)
    language: str | None = Field(None)
    llm_model: str | None = Field(None)


class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    id: str
    name: str
    description: str | None
    agri_area: str
    language: str
    llm_model: str | None = None
    created_at: datetime
    updated_at: datetime
    article_count: int = 0
    reviewed_count: int = 0

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
    llm_model: str | None = Field(None, description="Specific model to use for this query")


class GeneratedQuery(BaseModel):
    """Schema for a generated search query."""
    boolean_query: str = Field(..., description="Generated boolean/semantic query for display")
    concepts: list[str] = Field(default_factory=list, description="Extracted search concepts")
    synonyms: dict[str, list[str]] = Field(default_factory=dict, description="Synonyms per concept")
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
    adapted_queries_json: str | None = None
    created_at: datetime
    total_downloaded: int = 0
    unassigned_articles: int = 0

    model_config = {"from_attributes": True}


class SearchExecuteRequest(BaseModel):
    """Schema for executing a search across databases."""
    project_id: str = Field(..., description="Project UUID")
    query: str = Field(..., description="Search query to execute")
    raw_prompt: str | None = Field(None, description="Original natural language prompt typed by user")
    databases: list[str] = Field(
        default=["openalex", "semantic_scholar", "arxiv", "crossref",
                 "core", "scielo", "redalyc", "agecon", "organic_eprints"],
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
    local_pdf_path: str | None = None
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
    adapted_queries: dict[str, str] = Field(default_factory=dict, description="Query sent to each API")
    prompt_used: str | None = Field(None, description="Original NLP prompt typed by user")
    master_query: str | None = Field(None, description="Generated boolean query")


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
    not_found: int = 0
    in_progress: int
    articles: list[ArticleResponse] = []


# ──────────────────── Screening Schemas ────────────────────

class ScreeningEligibilityResponse(BaseModel):
    """Schema for checking if new screenings can be created."""
    total_downloaded: int = 0
    assigned_articles: int = 0
    eligible_articles: int = 0
    screening_names: list[str] = []


class CreateScreeningSessionRequest(BaseModel):
    """Schema for creating a new screening session."""
    project_id: str = Field(..., description="Project UUID")
    name: str = Field("Sesión de Screening", description="Descriptive session name")
    goal: str = Field("", description="Session objective / goal")
    search_query_ids: list[str] = Field(..., min_length=1, description="Selected search query IDs to include")
    reading_language: str = Field("es", description="Target language for abstract reading (es/en/pt)")
    translation_model: str = Field("aya:8b", description="Ollama model for translation")


class UpdateScreeningSessionRequest(BaseModel):
    """Schema for updating an existing session."""
    translation_model: str | None = Field(None, description="Ollama model for translation")


class ScreeningSessionResponse(BaseModel):
    """Schema for screening session API responses."""
    id: str
    project_id: str
    name: str | None = None
    goal: str | None = None
    search_query_ids: list[str]  # Parsed from JSON
    reading_language: str
    translation_model: str
    total_articles: int
    reviewed_count: int
    included_count: int
    excluded_count: int
    maybe_count: int
    created_at: datetime
    updated_at: datetime


class ScreeningDecisionResponse(BaseModel):
    """Schema for a single screening decision."""
    id: str
    session_id: str
    article_id: str
    decision: str
    exclusion_reason: str | None
    reviewer_note: str | None
    translated_abstract: str | None
    original_language: str | None
    display_order: int
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScreeningArticleResponse(BaseModel):
    """Schema for an article within a screening session (article + decision)."""
    # Article fields
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
    search_query_name: str | None = None
    download_status: str
    local_pdf_path: str | None
    # Decision fields
    decision_id: str
    decision: str = "pending"
    exclusion_reason: str | None = None
    reviewer_note: str | None = None
    translated_abstract: str | None = None
    display_order: int = 0
    decided_at: datetime | None = None


class UpdateDecisionRequest(BaseModel):
    """Schema for updating a screening decision."""
    decision: str = Field(..., description="Decision: include, exclude, or maybe")
    exclusion_reason: str | None = Field(None, description="Required when decision=exclude")
    reviewer_note: str | None = Field(None, description="Optional reviewer note")


class ScreeningStatsResponse(BaseModel):
    """Schema for screening session progress stats."""
    total: int
    reviewed: int
    pending: int
    included: int
    excluded: int
    maybe: int
    progress_percent: float


class TranslateAbstractRequest(BaseModel):
    """Schema for requesting abstract translation."""
    decision_id: str = Field(..., description="ScreeningDecision UUID")
    target_language: str = Field("es", description="Target language for translation")


class ScreeningSuggestionResponse(BaseModel):
    """Schema for AI relevance suggestion."""
    decision_id: str
    suggested_status: str  # include | exclude
    justification: str
    confidence: float | None = None
