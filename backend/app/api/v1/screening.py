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
    UpdateScreeningSessionRequest,
    ScreeningSuggestionResponse,
    ScreeningEligibilityResponse,
)
from app.services.active_learning_service import ActiveLearningService

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

@router.get("/eligibility/{project_id}", response_model=ScreeningEligibilityResponse)
async def check_screening_eligibility(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check how many articles are downloaded and if they are all assigned already."""
    from app.models.project import DownloadStatus
    
    # 1. Get total downloaded articles for project
    stmt_downloaded = select(func.count(Article.id)).where(
        Article.project_id == project_id,
        Article.download_status == DownloadStatus.SUCCESS,
        Article.is_duplicate == False
    )
    total_downloaded_res = await db.execute(stmt_downloaded)
    total_downloaded = total_downloaded_res.scalar_one_or_none() or 0
    
    # 2. Get assigned downloaded articles
    stmt_assigned = (
        select(func.count(func.distinct(ScreeningDecision.article_id)))
        .join(Article, ScreeningDecision.article_id == Article.id)
        .where(
            Article.project_id == project_id,
            Article.download_status == DownloadStatus.SUCCESS,
            Article.is_duplicate == False
        )
    )
    assigned_articles_res = await db.execute(stmt_assigned)
    assigned_articles = assigned_articles_res.scalar_one_or_none() or 0
    
    # 3. Get existing sessions
    stmt_sessions = select(ScreeningSession.name).where(ScreeningSession.project_id == project_id)
    session_names_res = await db.execute(stmt_sessions)
    screening_names = [name for name in session_names_res.scalars().all() if name]
    
    return ScreeningEligibilityResponse(
        total_downloaded=total_downloaded,
        assigned_articles=assigned_articles,
        eligible_articles=max(0, total_downloaded - assigned_articles),
        screening_names=screening_names
    )



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
    - Only articles with download_status=SUCCESS are included
    """
    logger.info("Creating screening session for project %s with %d searches",
                req.project_id, len(req.search_query_ids))

    # 1. Enrich articles from PDFs first (fill abstract, keywords, paths)
    from app.services.pdf_enrichment_service import enrich_articles_from_pdfs
    try:
        enrich_stats = await enrich_articles_from_pdfs(db, req.project_id)
        logger.info("Pre-screening enrichment: %s", enrich_stats)
    except Exception as e:
        logger.warning("Pre-screening enrichment failed (continuing anyway): %s", e)

    # 2. Gather unique, non-duplicate articles WITH PDF DOWNLOADED and UNASSIGNED from selected searches
    from app.models.project import DownloadStatus
    from app.models.screening_decision import ScreeningDecision
    
    stmt = (
        select(Article)
        .outerjoin(ScreeningDecision, Article.id == ScreeningDecision.article_id)
        .where(
            Article.project_id == req.project_id,
            Article.search_query_id.in_(req.search_query_ids),
            Article.is_duplicate == False,  # noqa: E712
            Article.download_status == DownloadStatus.SUCCESS,
            ScreeningDecision.id.is_(None)  # Only unassigned articles
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


@router.get("/sessions/project/{project_id}", response_model=list[ScreeningSessionResponse])
async def list_project_sessions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all screening sessions for a project."""
    result = await db.execute(
        select(ScreeningSession)
        .where(ScreeningSession.project_id == project_id)
        .order_by(ScreeningSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ScreeningSessionResponse)
async def get_screening_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get screening session details."""
    result = await db.execute(
        select(ScreeningSession).where(ScreeningSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de screening no encontrada.")
    return _session_to_response(session)


@router.patch("/sessions/{session_id}", response_model=ScreeningSessionResponse)
async def update_screening_session(
    session_id: str,
    req: UpdateScreeningSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update screening session (e.g., changing the translation model)."""
    result = await db.execute(
        select(ScreeningSession).where(ScreeningSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de screening no encontrada.")

    if req.translation_model is not None:
        session.translation_model = req.translation_model

    await db.commit()
    await db.refresh(session)
    logger.info("Updated screening session %s with model %s", session_id, req.translation_model)
    return _session_to_response(session)



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
        select(ScreeningDecision, Article, SearchQuery.raw_input)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .outerjoin(SearchQuery, Article.search_query_id == SearchQuery.id)
        .where(ScreeningDecision.session_id == session_id)
    )

    if filter_decision:
        stmt = stmt.where(ScreeningDecision.decision == filter_decision)

    stmt = stmt.order_by(ScreeningDecision.display_order).offset(skip).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    response = []
    for decision, article, sq_name in rows:
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
            search_query_name=sq_name,
            download_status=article.download_status.value if article.download_status else "pending",
            local_pdf_path=article.local_pdf_path,
            local_md_path=article.local_md_path,
            llm_summary=article.llm_summary,
            parsed_status=article.parsed_status,
            relevance_score=article.relevance_score,
            methodology_type=article.methodology_type,
            agri_variables_json=article.agri_variables_json,
            # Decision fields
            decision_id=decision.id,
            decision=decision.decision.value if decision.decision else "pending",
            exclusion_reason=decision.exclusion_reason,
            reviewer_note=decision.reviewer_note,
            translated_abstract=decision.translated_abstract,
            display_order=decision.display_order,
            decided_at=decision.decided_at,
        ))

    return response


@router.get("/sessions/{session_id}/articles/{article_id}/suggestion", response_model=ScreeningSuggestionResponse)
async def get_article_suggestion(
    session_id: str,
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI suggestion based on Active Learning (decision patterns)."""
    # 1. Get Session for Goal
    res_session = await db.execute(select(ScreeningSession).where(ScreeningSession.id == session_id))
    session = res_session.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    # 2. Get Labeled Articles for Training (limit to project)
    # We take articles that have a decision in ANY session of this project
    # to maximize training data for the model.
    stmt_labeled = (
        select(Article.title, Article.abstract, Article.keywords, ScreeningDecision.decision)
        .join(ScreeningDecision, Article.id == ScreeningDecision.article_id)
        .where(
            Article.project_id == session.project_id,
            ScreeningDecision.decision.in_([ScreeningDecisionStatus.INCLUDE, ScreeningDecisionStatus.EXCLUDE])
        )
    )
    res_labeled = await db.execute(stmt_labeled)
    labeled_data = [
        {"title": r.title, "abstract": r.abstract, "keywords": r.keywords, "decision": r.decision}
        for r in res_labeled.all()
    ]

    # 3. Get Target Article
    res_target = await db.execute(select(Article).where(Article.id == article_id))
    target = res_target.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    # 4. Use ActiveLearningService
    al_service = ActiveLearningService()
    if al_service.train(labeled_data):
        pool = [{"title": target.title, "abstract": target.abstract, "keywords": target.keywords}]
        predictions = al_service.predict_relevance(pool)
        pred = predictions[0]
        
        score = pred.get("suggestion_score", 0.5)
        status = "include" if score >= 0.5 else "exclude"
        # Calculate a rough justification based on score
        confidence = float(pred.get("uncertainty", 0))
        # High uncertainty means score near 0.5. 
        # Re-map uncertainty to actual confidence (1.0 = score 1 or 0, 0.0 = score 0.5)
        display_confidence = 1.0 - confidence 
        
        return ScreeningSuggestionResponse(
            decision_id=article_id, # Reused id field
            suggested_status=status,
            justification=f"Personalizado según tus {len(labeled_data)} decisiones previas (Relevancia: {score:.2f})",
            confidence=display_confidence
        )
    else:
        # Fallback to LLM few-shot if ML training failed (not enough diversity)
        from app.services.llm_service import generate_relevance_suggestion
        # Take last 5 decisions as context
        history = labeled_data[-5:] if labeled_data else []
        suggestion = await generate_relevance_suggestion(
            title=target.title,
            abstract=target.abstract or "",
            history=history,
            goal=session.goal
        )
        return ScreeningSuggestionResponse(
            decision_id=article_id,
            **suggestion
        )


@router.post("/sessions/{session_id}/rerank")
async def rerank_session_articles(
    session_id: str,
    mode: str = Query("uncertainty", pattern="^(uncertainty|most_relevant|balanced)$"),
    db: AsyncSession = Depends(get_db),
):
    """Rerank all pending articles in the session using Active Learning."""
    res_session = await db.execute(select(ScreeningSession).where(ScreeningSession.id == session_id))
    session = res_session.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    # 1. Get Labeled
    stmt_labeled = (
        select(Article.title, Article.abstract, Article.keywords, ScreeningDecision.decision)
        .join(ScreeningDecision, Article.id == ScreeningDecision.article_id)
        .where(
            Article.project_id == session.project_id,
            ScreeningDecision.decision.in_([ScreeningDecisionStatus.INCLUDE, ScreeningDecisionStatus.EXCLUDE])
        )
    )
    res_labeled = await db.execute(stmt_labeled)
    labeled_data = [
        {"title": r.title, "abstract": r.abstract, "keywords": r.keywords, "decision": r.decision}
        for r in res_labeled.all()
    ]

    al_service = ActiveLearningService()
    if not al_service.train(labeled_data):
        raise HTTPException(status_code=400, detail="Se necesitan al menos decisiones de 'incluir' y 'excluir' para entrenar el modelo.")

    # 2. Get Pending Decisions + Articles
    stmt_pending = (
        select(ScreeningDecision, Article)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .where(ScreeningDecision.session_id == session_id, ScreeningDecision.decision == ScreeningDecisionStatus.PENDING)
    )
    res_pending = await db.execute(stmt_pending)
    pending_rows = res_pending.all()
    
    if not pending_rows:
        return {"status": "ok", "message": "No hay artículos pendientes para re-rankear."}

    pool = []
    id_map = {}
    for decision, article in pending_rows:
        pool.append({"id": decision.id, "title": article.title, "abstract": article.abstract, "keywords": article.keywords})
        id_map[decision.id] = decision

    # 3. Predict and Rank
    scored_pool = al_service.predict_relevance(pool)
    ranked_pool = al_service.rank_for_screening(scored_pool, mode=mode)

    # 4. Update display_order
    # We find the current minimum display_order of pending to maintain consistency
    min_order = min([r[0].display_order for r in pending_rows])
    for i, item in enumerate(ranked_pool):
        decision = id_map[item['id']]
        decision.display_order = min_order + i

    await db.commit()
    logger.info("Session %s re-ranked using %s mode", session_id, mode)
    return {"status": "ok", "message": f"Session re-ordenada por {mode}."}


# ── Decision Updates ──


from fastapi.responses import FileResponse
import os

@router.get("/sessions/{session_id}/articles/{article_id}/pdf")
async def get_article_pdf(
    session_id: str,
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Serve the local PDF file for a specific article.
    """
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article or not article.local_pdf_path or not os.path.exists(article.local_pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found for this article.")

    return FileResponse(
        path=article.local_pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="document.pdf"'}
    )

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
        select(ScreeningDecision, Article, SearchQuery.raw_input)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .outerjoin(SearchQuery, Article.search_query_id == SearchQuery.id)
        .where(ScreeningDecision.id == decision_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Decisión de screening no encontrada.")

    decision, article, sq_name = row

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
        search_query_name=sq_name,
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




@router.post("/sessions/{session_id}/analyze")
async def analyze_session_articles(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger deep analysis for all articles in a session.
    Parses PDF -> MD and runs LLM extraction/scoring.
    """
    from app.services.pdf_parser import pdf_parser
    from app.services.llm_service import analyze_article_content

    # 1. Get Session
    session_res = await db.execute(select(ScreeningSession).where(ScreeningSession.id == session_id))
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    # 2. Get Articles in Session
    stmt = (
        select(Article)
        .join(ScreeningDecision, Article.id == ScreeningDecision.article_id)
        .where(ScreeningDecision.session_id == session_id)
    )
    res_articles = await db.execute(stmt)
    articles = res_articles.scalars().all()

    stats = {"processed": 0, "parsed": 0, "analyzed": 0, "failed": 0}

    # Use sync session wrapper for services
    import sqlalchemy.orm
    sync_session_factory = sqlalchemy.orm.sessionmaker(bind=db.bind, sync_session_class=sqlalchemy.orm.Session)
    
    for article in articles:
        try:
            # A. Parse to MD if needed
            if not article.local_md_path or article.parsed_status != "success":
                # We need to bridge to sync session or adapt service
                # For this task, I'll just use the article object and commit later
                success = await pdf_parser.parse_article(article, db)
                if success:
                    stats["parsed"] += 1
                else:
                    stats["failed"] += 1
                    continue

            # B. Analyze with LLM if parsed
            if article.local_md_path and (not article.llm_summary or article.relevance_score == 0.0):
                with open(article.local_md_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                
                analysis = await analyze_article_content(
                    md_content=md_text,
                    project_goal=session.goal
                )
                
                article.llm_summary = analysis.get("llm_summary")
                article.relevance_score = analysis.get("relevance_score", 0.0)
                article.methodology_type = analysis.get("methodology_type")
                article.agri_variables_json = json.dumps(analysis.get("agri_variables", {}))
                
                stats["analyzed"] += 1
            
            stats["processed"] += 1
            await db.commit() # Persistent update per article to show progress

        except Exception as e:
            logger.error(f"Analysis failed for article {article.id}: {e}")
            stats["failed"] += 1

    return stats
