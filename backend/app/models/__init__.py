"""
Modelos SQLAlchemy para AgriSearch.

Importar aquí asegura que todos los modelos estén registrados en Base.metadata
antes de que init_db() cree las tablas.
"""

from app.models.project import (
    Project,
    Article,
    SearchQuery,
    ScreeningSession,
    ScreeningDecision,
    SearchSession,
    SearchResultRaw,
    AgriArea,
    DownloadStatus,
    ScreeningDecisionStatus,
)
from app.models.article_reference import ArticleReference

__all__ = [
    "Project",
    "Article",
    "SearchQuery",
    "ScreeningSession",
    "ScreeningDecision",
    "SearchSession",
    "SearchResultRaw",
    "ArticleReference",
    "AgriArea",
    "DownloadStatus",
    "ScreeningDecisionStatus",
]
