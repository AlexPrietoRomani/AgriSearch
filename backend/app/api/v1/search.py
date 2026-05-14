"""
Archivo: search.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Punto de entrada para la orquestación de búsquedas científicas y gestión de documentos
en AgriSearch. Este módulo expone los endpoints necesarios para la generación de
consultas inteligentes mediante LLM, la ejecución federada en bases de datos (ArXiv,
OpenAlex, Semantic Scholar) y el ciclo de vida de los PDFs (descarga y conversión).

Acciones Principales:
    - `build_query`: Transforma lenguaje natural en búsquedas booleanas optimizadas.
    - `execute_search_endpoint`: Ejecuta la búsqueda federada y almacena resultados.
    - `list_articles`: Recupera artículos filtrados y paginados por proyecto.
    - `download_pdfs`: Inicia procesos de descarga masiva de PDFs Open Access.
    - `upload_pdf`: Permite la vinculación manual de archivos PDF locales.
    - `reparse_pdfs`: Lanza tareas de fondo para convertir PDFs a Markdown.

Estructura Interna:
    - `build_query`: Generación de queries con LLM.
    - `execute_search_endpoint`: Búsqueda federada.
    - `list_articles`: Recuperación de artículos de la BD.
    - `download_pdfs`: Orquestación de descargas.

Entradas / Dependencias:
    - `app.services.search_service`: Lógica de negocio.
    - `app.services.llm_service`: IA Generativa.
    - `app.services.download_service`: Gestión de archivos.

Salidas / Efectos:
    - Registra metadatos de artículos en SQLite.
    - Genera archivos PDF en el sistema de archivos local.
    - Crea tareas en segundo plano para el procesamiento de documentos.

Integración UI:
    - Consumido por el 'SearchWizard' y la 'DocumentLibrary' en el frontend.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, BackgroundTasks
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
    Utiliza el LLM para transformar una pregunta de investigación en lenguaje natural
    en una consulta de búsqueda booleana optimizada con términos AGROVOC y desglose PICO.

    Args:
        payload (SearchBuildQueryRequest): Datos de la petición con el input del usuario.

    Returns:
        GeneratedQuery: La consulta estructurada devuelta por el modelo de IA.
    """
    logger.info(
        "[build-query] received llm_model=%r agri_area=%r years=%s-%s",
        payload.llm_model,
        payload.agri_area,
        payload.year_from,
        payload.year_to,
    )
    
    result = await generate_search_query(
        user_input=payload.user_input,
        agri_area=payload.agri_area,
        language=payload.language,
        year_from=payload.year_from,
        year_to=payload.year_to,
        model=payload.llm_model,
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
    "/preview-queries",
    summary="Preview adapted queries per database without executing the search",
)
async def preview_queries(payload: dict) -> dict:
    """
    Previsualiza las consultas adaptadas para cada base de datos a partir de
    una query booleana maestra, sin ejecutar la búsqueda real.

    Útil para mostrar al usuario exactamente qué se enviará a cada API
    antes de confirmar la ejecución.

    Args:
        payload (dict): Debe contener `boolean_query` (str) y `databases` (list[str]).

    Returns:
        dict: Mapa de base de datos → consulta adaptada.
    """
    from app.services.search_service import _parse_boolean_query_structure
    from app.services.query_builder import build_all_queries

    boolean_query: str = payload.get("boolean_query", "")
    databases: list[str] = payload.get("databases", [])

    if not boolean_query or not databases:
        return {"adapted_queries": {}}

    concepts, synonyms = _parse_boolean_query_structure(boolean_query)
    adapted_queries = build_all_queries(concepts=concepts, synonyms=synonyms, databases=databases)

    return {"adapted_queries": adapted_queries}




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
    Ejecuta la consulta de búsqueda a través de las bases de datos seleccionadas
    (OpenAlex, Semantic Scholar, ArXiv).
    
    Elimina duplicados basados en el DOI y coincidencias difusas (fuzzy matching)
    del título. Almacena los resultados en la base de datos del proyecto.

    Args:
        payload (SearchExecuteRequest): Los parámetros de la búsqueda a ejecutar.
        db (AsyncSession): Sesión asíncrona de base de datos inyectada.

    Returns:
        SearchResultsResponse: Estadísticas y lista de artículos encontrados.

    Raises:
        HTTPException: Si el proyecto no existe (404) o hay un error en la búsqueda (500).
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
        master_query=payload.query
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
    """
    Obtiene los artículos de un proyecto con paginación.
    
    Permite el filtrado opcional por el estado de descarga del PDF o 
    el ID de la consulta de búsqueda que los originó.

    Args:
        project_id (str): ID del proyecto.
        skip (int): Número de registros a saltar (paginación).
        limit (int): Número máximo de registros a devolver.
        download_status (str | None, opcional): Filtrar por estado de descarga.
        search_query_id (str | None, opcional): Filtrar por búsqueda específica.
        db (AsyncSession): Sesión asíncrona de base de datos.

    Returns:
        dict: Un diccionario con la lista de artículos, total y metadatos de paginación.
    """
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
    Descarga los PDFs de acceso abierto (Open Access) para los artículos de un proyecto.
    
    Si no se proporciona un array `article_ids`, intenta descargar todos los 
    artículos pendientes que posean una URL de Open Access.

    Args:
        payload (DownloadRequest): Petición con el ID del proyecto y opcionalmente IDs de artículos.
        db (AsyncSession): Sesión asíncrona de base de datos inyectada.

    Returns:
        DownloadProgressResponse: Estadísticas del proceso de descarga.

    Raises:
        HTTPException: Si el proceso de descarga falla estrepitosamente (500).
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
    "/force-download/{article_id}",
    summary="Force-download an article via Sci-Hub using DOI",
)
async def force_download_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Fuerza la descarga de un artículo usando Sci-Hub (último recurso).
    Solo funciona si el artículo tiene DOI.
    Marca download_status como 'manual' en caso de éxito.
    """
    from sqlalchemy import select
    from app.models.project import Article, DownloadStatus
    from app.core.config import get_settings
    from app.services.scihub_service import SciHubDownloader
    from pathlib import Path

    settings = get_settings()

    if not settings.scihub_enabled:
        raise HTTPException(status_code=403, detail="Sci-Hub descarga no está habilitada")

    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    if not article.doi:
        raise HTTPException(status_code=400, detail="El artículo no tiene DOI para buscar en Sci-Hub")

    try:
        scihub = SciHubDownloader(
            download_dir=Path(settings.scihub_download_dir),
            rate_limit=settings.scihub_rate_limit,
        )
        pdf_path = await scihub.download_and_save(article.doi, article.id)
        if pdf_path:
            article.download_status = DownloadStatus.MANUAL.value
            article.local_pdf_path = pdf_path
            await db.commit()
            return {"status": "success", "path": pdf_path}
        else:
            return {"status": "not_found", "reason": "Sci-Hub no encontró el PDF"}
    except Exception as e:
        logger.error("Sci-Hub error para %s: %s", article.doi, e)
        return {"status": "error", "reason": str(e)}


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
    """
    Permite subir manualmente un archivo PDF y vincularlo al ID de un artículo específico.

    Ideal para artículos bajo muro de pago (paywall) que el usuario obtuvo externamente.

    Args:
        article_id (str): El ID del artículo a vincular.
        file (UploadFile): El archivo binario cargado por el usuario (debe ser .pdf).
        db (AsyncSession): Sesión asíncrona de base de datos inyectada.

    Returns:
        ArticleResponse: Los detalles del artículo con su estado de descarga actualizado.

    Raises:
        HTTPException: Si el archivo no es PDF (400), no existe el artículo (404), o falla el guardado (500).
    """
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
    """
    Borra una consulta de búsqueda específica junto con todos sus artículos asociados y 
    archivos físicos (PDFs descargados).

    Args:
        project_id (str): ID del proyecto contenedor.
        query_id (str): ID de la búsqueda a eliminar.
        db (AsyncSession): Sesión asíncrona de base de datos inyectada.

    Returns:
        dict: Un diccionario con el estado de la operación.

    Raises:
        HTTPException: Si la búsqueda no existe (404) o hay error de eliminación (500).
    """
    try:
        await delete_search_query(db=db, project_id=project_id, query_id=query_id)
        return {"status": "success", "message": "Search query deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete search query: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to delete search query")

@router.post(
    "/reparse/{project_id}",
    summary="Force re-parsing of all downloaded PDFs to Markdown"
)
async def reparse_pdfs(
    project_id: str,
    background_tasks: BackgroundTasks,
    article_id: str | None = Query(None, description="ID del artículo específico a reparsar (opcional)"),
) -> dict:
    """
    Fuerza el re-procesamiento de todos los PDFs descargados en el proyecto 
    hacia formato Markdown a través de una tarea en segundo plano.

    Útil si hubo errores previos en la extracción o se actualizaron los extractores.

    Args:
        project_id (str): El ID del proyecto.
        background_tasks (BackgroundTasks): Cola de tareas en segundo plano de FastAPI.
        article_id (str | None, opcional): ID de un artículo específico si solo se desea reparsar ese.

    Returns:
        dict: Mensaje de confirmación de inicio de la tarea.
    """
    from app.services.pdf_enrichment_service import enrich_articles_from_pdfs
    from app.api.v1.events import publish_event
    from app.db.database import async_session_factory
    import asyncio

    async def run_reparse():
        # Give SSE time to connect (increased to 1.5s to avoid missing the 'reparse_start' event if frontend routing/render is delayed)
        await asyncio.sleep(1.5)
        async with async_session_factory() as session:
            try:
                await publish_event(project_id, {"type": "reparse_start", "msg": "Iniciando proceso de conversión de PDFs a Markdown..."})
                
                # Pasar article_ids si viene un artículo específico
                art_ids = [article_id] if article_id else None
                stats = await enrich_articles_from_pdfs(session, project_id, article_ids=art_ids, force_reparse=True)
                await publish_event(project_id, {"type": "reparse_end", "msg": "¡Proceso terminado!", "stats": stats})
            except Exception as e:
                logger.error(f"Background reparse failed for {project_id}: {e}")
                await publish_event(project_id, {"type": "error", "msg": f"Error en el procesamiento: {str(e)}"})

    background_tasks.add_task(run_reparse)
    return {"status": "accepted", "message": "Procesamiento iniciado en segundo plano"}

@router.post("/cancel-reparse/{project_id}")
async def cancel_reparse(project_id: str):
    """
    Emite una señal para detener cualquier proceso de re-procesamiento (reparse)
    activo para este proyecto en particular.

    Args:
        project_id (str): ID del proyecto cuyo proceso se desea cancelar.

    Returns:
        dict: Estado de la operación de cancelación.
    """
    from app.services.pdf_enrichment_service import cancel_enrichment
    cancel_enrichment(project_id)
    return {"status": "cancelled"}

