"""
AgriSearch Backend - Screening API endpoints.

Handles screening session creation, article decisions, and abstract translation.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.project import (
    Article,
    ScreeningDecision,
    ScreeningDecisionStatus,
    ScreeningSession,
    SearchQuery,
)
from app.models.schemas import (
    CreateScreeningSessionRequest,
    ScreeningArticleResponse,
    ScreeningSessionResponse,
    ScreeningStatsResponse,
    UpdateDecisionRequest,
    TranslateAbstractRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screening", tags=["Screening"])


# ── Helpers ──

def _session_to_response(session: ScreeningSession) -> ScreeningSessionResponse:
    """Convert a ScreeningSession ORM object to a response schema."""
    return ScreeningSessionResponse(
        id=session.id,
        project_id=session.project_id,
        name=session.name,
        goal=session.goal,
        search_query_ids=json.loads(session.search_query_ids),
        reading_language=session.reading_language,
        translation_model=session.translation_model,
        total_articles=session.total_articles,
        reviewed_count=session.reviewed_count,
        included_count=session.included_count,
        excluded_count=session.excluded_count,
        maybe_count=session.maybe_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


# ── Session Endpoints ──


@router.post("/enrich/{project_id}")
async def enrich_project_articles(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Enrich articles with data extracted from their PDFs (abstract, keywords, paths)."""
    from app.services.pdf_enrichment_service import enrich_articles_from_pdfs

    try:
        stats = await enrich_articles_from_pdfs(db, project_id)
        await db.commit()
        return stats
    except Exception as e:
        logger.error("Enrichment failed for project %s: %s", project_id, e)
        raise HTTPException(status_code=500, detail=f"Error durante el enriquecimiento: {str(e)}")


@router.post("/sessions", response_model=ScreeningSessionResponse, status_code=201)
async def create_screening_session(
    req: CreateScreeningSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new screening session from selected search queries.
    
    Rules:
    - Only 1 active session per project (returns 409 if one already exists)
    - Only articles with download_status=SUCCESS are included
    """
    logger.info("Creating screening session for project %s with %d searches",
                req.project_id, len(req.search_query_ids))

    # 0. Check no other session exists for this project
    existing = await db.execute(
        select(ScreeningSession).where(ScreeningSession.project_id == req.project_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Ya existe una sesión de screening activa para este proyecto. Elimínala primero para crear una nueva."
        )

    # 1. Enrich articles from PDFs first (fill abstract, keywords, paths)
    from app.services.pdf_enrichment_service import enrich_articles_from_pdfs
    try:
        enrich_stats = await enrich_articles_from_pdfs(db, req.project_id)
        logger.info("Pre-screening enrichment: %s", enrich_stats)
    except Exception as e:
        logger.warning("Pre-screening enrichment failed (continuing anyway): %s", e)

    # 2. Gather unique, non-duplicate articles WITH PDF DOWNLOADED from selected searches
    from app.models.project import DownloadStatus
    stmt = (
        select(Article)
        .where(
            Article.project_id == req.project_id,
            Article.search_query_id.in_(req.search_query_ids),
            Article.is_duplicate == False,  # noqa: E712
            Article.download_status == DownloadStatus.SUCCESS,
        )
    )
    result = await db.execute(stmt)
    articles = result.scalars().all()

    if not articles:
        raise HTTPException(status_code=400, detail="No se encontraron artículos con PDF descargado en las búsquedas seleccionadas.")

    # 3. Create the session
    session = ScreeningSession(
        project_id=req.project_id,
        name=req.name,
        goal=req.goal,
        search_query_ids=json.dumps(req.search_query_ids),
        reading_language=req.reading_language,
        translation_model=req.translation_model,
        total_articles=len(articles),
    )
    db.add(session)
    await db.flush()  # Get session.id

    # 4. Create a ScreeningDecision for each article
    for idx, article in enumerate(articles):
        decision = ScreeningDecision(
            session_id=session.id,
            article_id=article.id,
            display_order=idx,
        )
        db.add(decision)

    await db.commit()
    await db.refresh(session)

    logger.info("Created screening session %s with %d articles (only PDFs)", session.id, len(articles))
    return _session_to_response(session)


@router.delete("/sessions/{session_id}", status_code=200)
async def delete_screening_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a screening session and all its decisions. IRREVERSIBLE."""
    result = await db.execute(
        select(ScreeningSession).where(ScreeningSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de screening no encontrada.")

    await db.delete(session)
    await db.commit()
    logger.info("Deleted screening session %s (cascade deletes decisions)", session_id)
    return {"status": "ok", "message": "Sesión eliminada correctamente."}



# ── Articles within a Session ──


@router.get("/sessions/{session_id}/articles", response_model=list[ScreeningArticleResponse])
async def list_screening_articles(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
    filter_decision: str | None = Query(None, description="Filter by decision: pending, include, exclude, maybe"),
    db: AsyncSession = Depends(get_db),
):
    """List articles in a screening session with their decisions."""
    # Build the query joining decisions with articles
    stmt = (
        select(ScreeningDecision, Article)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .where(ScreeningDecision.session_id == session_id)
    )

    if filter_decision:
        stmt = stmt.where(ScreeningDecision.decision == filter_decision)

    stmt = stmt.order_by(ScreeningDecision.display_order).offset(skip).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    response = []
    for decision, article in rows:
        response.append(ScreeningArticleResponse(
            id=article.id,
            doi=article.doi,
            title=article.title,
            authors=article.authors,
            year=article.year,
            abstract=article.abstract,
            journal=article.journal,
            url=article.url,
            keywords=article.keywords,
            source_database=article.source_database,
            download_status=article.download_status.value if article.download_status else "pending",
            local_pdf_path=article.local_pdf_path,
            decision_id=decision.id,
            decision=decision.decision.value if decision.decision else "pending",
            exclusion_reason=decision.exclusion_reason,
            reviewer_note=decision.reviewer_note,
            translated_abstract=decision.translated_abstract,
            display_order=decision.display_order,
            decided_at=decision.decided_at,
        ))

    return response


# ── Decision Updates ──


@router.put("/decisions/{decision_id}", response_model=ScreeningArticleResponse)
async def update_decision(
    decision_id: str,
    req: UpdateDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a screening decision for an article."""
    # Validate decision value
    valid_decisions = {"include", "exclude", "maybe", "pending"}
    if req.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Decisión inválida: '{req.decision}'. Valores válidos: {valid_decisions}",
        )

    if req.decision == "exclude" and not req.exclusion_reason:
        raise HTTPException(
            status_code=400,
            detail="Se requiere un motivo de exclusión cuando la decisión es 'excluir'.",
        )

    # Fetch decision + article
    result = await db.execute(
        select(ScreeningDecision, Article)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .where(ScreeningDecision.id == decision_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Decisión de screening no encontrada.")

    decision, article = row

    # Track if this is a new decision (was pending before)
    was_pending = decision.decision == ScreeningDecisionStatus.PENDING
    old_decision = decision.decision

    # Update the decision
    decision.decision = ScreeningDecisionStatus(req.decision)
    decision.exclusion_reason = req.exclusion_reason
    if req.reviewer_note is not None:
        decision.reviewer_note = req.reviewer_note
    decision.decided_at = datetime.now(timezone.utc)

    # Update session counters
    session_result = await db.execute(
        select(ScreeningSession).where(ScreeningSession.id == decision.session_id)
    )
    session = session_result.scalar_one()

    # Decrement old counter (if not pending)
    if old_decision == ScreeningDecisionStatus.INCLUDE:
        session.included_count = max(0, session.included_count - 1)
    elif old_decision == ScreeningDecisionStatus.EXCLUDE:
        session.excluded_count = max(0, session.excluded_count - 1)
    elif old_decision == ScreeningDecisionStatus.MAYBE:
        session.maybe_count = max(0, session.maybe_count - 1)

    # Increment new counter
    if req.decision == "include":
        session.included_count += 1
    elif req.decision == "exclude":
        session.excluded_count += 1
    elif req.decision == "maybe":
        session.maybe_count += 1

    # Update reviewed count
    if was_pending and req.decision != "pending":
        session.reviewed_count += 1
    elif not was_pending and req.decision == "pending":
        session.reviewed_count = max(0, session.reviewed_count - 1)

    await db.commit()
    await db.refresh(decision)

    return ScreeningArticleResponse(
        id=article.id,
        doi=article.doi,
        title=article.title,
        authors=article.authors,
        year=article.year,
        abstract=article.abstract,
        journal=article.journal,
        url=article.url,
        keywords=article.keywords,
        source_database=article.source_database,
        download_status=article.download_status.value if article.download_status else "pending",
        local_pdf_path=article.local_pdf_path,
        decision_id=decision.id,
        decision=decision.decision.value,
        exclusion_reason=decision.exclusion_reason,
        reviewer_note=decision.reviewer_note,
        translated_abstract=decision.translated_abstract,
        display_order=decision.display_order,
        decided_at=decision.decided_at,
    )


# ── Stats ──


@router.get("/sessions/{session_id}/stats", response_model=ScreeningStatsResponse)
async def get_screening_stats(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get screening session progress statistics."""
    result = await db.execute(
        select(ScreeningSession).where(ScreeningSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de screening no encontrada.")

    pending = session.total_articles - session.reviewed_count
    progress = (session.reviewed_count / session.total_articles * 100) if session.total_articles > 0 else 0

    return ScreeningStatsResponse(
        total=session.total_articles,
        reviewed=session.reviewed_count,
        pending=pending,
        included=session.included_count,
        excluded=session.excluded_count,
        maybe=session.maybe_count,
        progress_percent=round(progress, 1),
    )


# ── Translation ──


@router.post("/translate")
async def translate_abstract(
    req: TranslateAbstractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Translate an article's abstract using the configured LLM model."""
    # Fetch decision + article + session
    result = await db.execute(
        select(ScreeningDecision, Article, ScreeningSession)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .join(ScreeningSession, ScreeningDecision.session_id == ScreeningSession.id)
        .where(ScreeningDecision.id == req.decision_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Decisión de screening no encontrada.")

    decision, article, session = row

    # Return cached translation if available
    if decision.translated_abstract:
        return {
            "decision_id": decision.id,
            "translated_abstract": decision.translated_abstract,
            "cached": True,
        }

    if not article.abstract:
        return {
            "decision_id": decision.id,
            "translated_abstract": None,
            "cached": False,
            "error": "El artículo no tiene abstract.",
        }

    # Translate using LLM
    from app.services.llm_service import translate_text

    language_names = {"es": "español", "en": "inglés", "pt": "portugués"}
    target_name = language_names.get(req.target_language, req.target_language)

    try:
        translated = await translate_text(
            text=article.abstract,
            target_language=target_name,
            model=session.translation_model,
        )

        # Cache the translation
        decision.translated_abstract = translated
        decision.original_language = "en"  # Assume English for now; can be improved with langdetect
        await db.commit()

        return {
            "decision_id": decision.id,
            "translated_abstract": translated,
            "cached": False,
        }
    except Exception as e:
        logger.error("Translation failed for decision %s: %s", decision.id, e)
        raise HTTPException(status_code=500, detail=f"Error de traducción: {str(e)}")
