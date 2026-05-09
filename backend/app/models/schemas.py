"""
Archivo: schemas.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Esquemas de validación y serialización de datos basados en Pydantic para la API
de AgriSearch. Estos modelos actúan como contratos de interfaz, asegurando la
integridad de las peticiones (request) y la estructura consistente de las
respuestas (response), manteniendo el desacoplamiento con los modelos de BD.

Acciones Principales:
    - Validación de entrada para creación de proyectos y búsquedas.
    - Definición de tipos para la comunicación entre el frontend y el backend.
    - Configuración de compatibilidad ORM para serialización automática.
    - Desglose de estructuras complejas (PICO, Diagnósticos, Sugerencias de IA).

Estructura Interna:
    - `ProjectSchemas`: Gestión de proyectos.
    - `SearchSchemas`: Consultas y resultados federados.

Entradas / Dependencias:
    - `pydantic`: Motor de validación.
    - `datetime`: Para el manejo de marcas de tiempo serializadas.

Salidas / Efectos:
    - Garantiza que los datos que entran y salen de la API cumplen con el tipo esperado.
    - Lanza errores de validación automáticos en caso de discrepancia de datos.

Ejemplo de Integración:
    from app.models.schemas import SearchExecuteRequest
    request = SearchExecuteRequest(project_id="uuid", query="soil health")
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ──────────────────── Esquemas de Proyecto ────────────────────


class ProjectCreate(BaseModel):
    """Esquema para la creación de un nuevo proyecto."""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del proyecto")
    description: str | None = Field(None, description="Descripción opcional")
    agri_area: str = Field("general", description="Área agrícola de enfoque")
    language: str = Field("es", description="Idioma principal (BCP-47)")
    llm_model: str | None = Field(None, description="Modelo LLM preferido para este proyecto")


class ProjectUpdate(BaseModel):
    """Esquema para actualizar un proyecto existente."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    agri_area: str | None = Field(None)
    language: str | None = Field(None)
    llm_model: str | None = Field(None)


class ProjectResponse(BaseModel):
    """Esquema para las respuestas de la API de proyectos."""
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
    """Esquema para el listado de proyectos."""
    projects: list[ProjectResponse]
    total: int


# ──────────────────── Esquemas de Búsqueda ────────────────────


class SearchBuildQueryRequest(BaseModel):
    """Esquema para solicitar la generación de consultas a partir de lenguaje natural."""
    user_input: str = Field(..., min_length=5, description="Descripción del tema de investigación")
    agri_area: str = Field("general", description="Área agrícola para contexto")
    year_from: int | None = Field(None, description="Año inicial del filtro")
    year_to: int | None = Field(None, description="Año final del filtro")
    language: str = Field("es", description="Idioma preferido para la generación")
    llm_model: str | None = Field(None, description="Modelo específico a usar para esta consulta")


class GeneratedQuery(BaseModel):
    """Esquema para una consulta de búsqueda generada."""
    boolean_query: str = Field(..., description="Consulta booleana/semántica generada")
    concepts: list[str] = Field(default_factory=list, description="Conceptos de búsqueda extraídos")
    synonyms: dict[str, list[str]] = Field(default_factory=dict, description="Sinónimos por concepto")
    suggested_terms: list[str] = Field(default_factory=list, description="Términos sugeridos (AGROVOC/MeSH)")
    pico_breakdown: dict[str, str] = Field(default_factory=dict, description="Desglose PICO/PEO")
    explanation: str = Field("", description="Explicación de la consulta generada")


class SearchQueryResponse(BaseModel):
    """Esquema para la respuesta de una consulta de búsqueda guardada."""
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
    """Esquema para ejecutar una búsqueda en las bases de datos científicas."""
    project_id: str = Field(..., description="UUID del proyecto")
    query: str = Field(..., description="Consulta de búsqueda a ejecutar")
    raw_prompt: str | None = Field(None, description="Prompt original del usuario")
    databases: list[str] = Field(
        default=["openalex", "semantic_scholar", "arxiv", "crossref",
                 "core", "scielo", "redalyc", "agecon", "organic_eprints"],
        description="Bases de datos donde buscar",
    )
    max_results_per_source: int = Field(50, ge=10, le=500, description="Máximo de resultados por fuente")
    year_from: int | None = None
    year_to: int | None = None


class ArticleResponse(BaseModel):
    """Esquema para un artículo científico en las respuestas de la API."""
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
    local_md_path: str | None = None
    llm_summary: str | None = None
    parsed_status: str = "pending"
    relevance_score: float = 0.0
    methodology_type: str | None = None
    agri_variables_json: str | None = None
    is_duplicate: bool
    document_type: str | None = "journal-article"
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResultsResponse(BaseModel):
    """Esquema para los resultados de la ejecución de una búsqueda."""
    project_id: str
    query_id: str
    total_found: int
    duplicates_removed: int
    articles: list[ArticleResponse]
    counts_by_source: dict[str, int]
    adapted_queries: dict[str, str] = Field(default_factory=dict, description="Consulta enviada a cada API")
    prompt_used: str | None = Field(None, description="Prompt NLP original")
    master_query: str | None = Field(None, description="Consulta booleana maestra")


# ──────────────────── Esquemas de Descarga ────────────────────


class DownloadRequest(BaseModel):
    """Esquema para solicitar la descarga de artículos."""
    project_id: str
    article_ids: list[str] | None = Field(None, description="Artículos específicos a descargar. None = todos los pendientes.")


class DownloadProgressResponse(BaseModel):
    """Esquema para las actualizaciones del progreso de descarga."""
    total: int
    downloaded: int
    failed: int
    paywall: int
    not_found: int = 0
    in_progress: int
    articles: list[ArticleResponse] = []


# ──────────────────── Esquemas de Cribado (Screening) ────────────────────

class ScreeningEligibilityResponse(BaseModel):
    """Esquema para verificar si se pueden crear nuevos cribados."""
    total_downloaded: int = 0
    assigned_articles: int = 0
    eligible_articles: int = 0
    screening_names: list[str] = []


class CreateScreeningSessionRequest(BaseModel):
    """Esquema para crear una nueva sesión de cribado."""
    project_id: str = Field(..., description="UUID del proyecto")
    name: str = Field("Sesión de Screening", description="Nombre descriptivo de la sesión")
    goal: str = Field("", description="Objetivo o meta de la sesión")
    search_query_ids: list[str] = Field(..., min_length=1, description="IDs de consultas de búsqueda seleccionadas")
    reading_language: str = Field("es", description="Idioma para la lectura de abstracts (es/en/pt)")
    translation_model: str = Field("aya:8b", description="Modelo de Ollama para traducción")


class UpdateScreeningSessionRequest(BaseModel):
    """Esquema para actualizar una sesión existente."""
    translation_model: str | None = Field(None, description="Modelo de Ollama para traducción")


class ScreeningSessionResponse(BaseModel):
    """Esquema para las respuestas de la API de sesiones de cribado."""
    id: str
    project_id: str
    name: str | None = None
    goal: str | None = None
    search_query_ids: list[str]
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
    """Esquema para una decisión individual de cribado."""
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
    """Esquema para un artículo dentro de una sesión de cribado (artículo + decisión)."""
    # Campos del Artículo
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
    local_md_path: str | None = None
    llm_summary: str | None = None
    parsed_status: str = "pending"
    relevance_score: float = 0.0
    methodology_type: str | None = None
    agri_variables_json: str | None = None
    document_type: str | None = "journal-article"
    # Campos de la Decisión
    decision_id: str
    decision: str = "pending"
    exclusion_reason: str | None = None
    reviewer_note: str | None = None
    translated_abstract: str | None = None
    display_order: int = 0
    decided_at: datetime | None = None


class UpdateDecisionRequest(BaseModel):
    """Esquema para actualizar una decisión de cribado."""
    decision: str = Field(..., description="Decisión: include, exclude, o maybe")
    exclusion_reason: str | None = Field(None, description="Obligatorio si decision=exclude")
    reviewer_note: str | None = Field(None, description="Nota opcional del revisor")


class ScreeningStatsResponse(BaseModel):
    """Esquema para las estadísticas de progreso de la sesión de cribado."""
    total: int
    reviewed: int
    pending: int
    included: int
    excluded: int
    maybe: int
    progress_percent: float


class TranslateAbstractRequest(BaseModel):
    """Esquema para solicitar la traducción de un abstract."""
    decision_id: str = Field(..., description="UUID de la ScreeningDecision")
    target_language: str = Field("es", description="Idioma destino para la traducción")


class ScreeningSuggestionResponse(BaseModel):
    """Esquema para la sugerencia de relevancia generada por IA."""
    decision_id: str
    suggested_status: str  # include | exclude
    justification: str
    confidence: float | None = None


# ──────────────────── Esquemas de OA Resolution ────────────────────


class OAResolveResult(BaseModel):
    """Esquema para el resultado de una resolución OA via Unpaywall."""
    doi: str
    open_access_url: str | None = None
    resolved_by: str = "unpaywall"
