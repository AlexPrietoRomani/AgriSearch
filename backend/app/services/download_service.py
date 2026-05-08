"""
Archivo: download_service.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Servicio encargado de la descarga automatizada de artículos científicos en formato PDF.
Gestiona el acceso a URLs de acceso abierto, valida la integridad de los archivos
y orquestra el procesamiento posterior (parseo, análisis y RAG).

Acciones Principales:
    - Descarga asíncrona de PDFs con control de concurrencia (Semáforos).
    - Validación de tipos MIME y bytes mágicos de PDF.
    - Sanitización de nombres de archivos basada en metadatos (Autor_Año_Título).
    - Disparo automático del pipeline de enriquecimiento tras una descarga exitosa.

Estructura Interna:
    - `_download_single_pdf`: Lógica individual de descarga y validación.
    - `download_articles`: Orquestador principal de descargas y procesamiento post-descarga.
    - `_sanitize_filename`: Utilidad para nombres de archivo seguros.

Entradas / Dependencias:
    - Librería `aiohttp`.
    - Base de datos (SQLAlchemy AsyncSession).
    - `pdf_parser`, `llm_service`, `vector_service`.

Salidas / Efectos:
    - Persiste archivos `.pdf` y `.md` en directorios específicos del proyecto.
    - Actualiza estados de descarga y metadatos de enriquecimiento en la DB.
    - Indexa el contenido en el motor vectorial (RAG).

Ejemplo de Integración:
    results = await download_articles(db_session, project_id)
"""

import asyncio
import logging
import re
from pathlib import Path

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.project import Article, DownloadStatus

logger = logging.getLogger(__name__)
settings = get_settings()

# Semáforo para limitar la tasa de descargas concurrentes
_download_semaphore = asyncio.Semaphore(settings.download_rate_limit)

PDF_MAGIC_BYTES = b"%PDF"


def _sanitize_filename(text: str) -> str:
    """
    Crea un nombre de archivo seguro eliminando caracteres inválidos.

    Args:
        text (str): Texto original (ej: título).

    Returns:
        str: Texto sanitizado limitado a 100 caracteres.
    """
    safe = re.sub(r'[<>:"/\\|?*]', '_', text)
    safe = re.sub(r'\s+', '_', safe)
    return safe[:100]


async def _download_single_pdf(
    session: aiohttp.ClientSession,
    article: Article,
    pdf_dir: Path,
) -> tuple[str, str, str]:
    """
    Descarga un único PDF para un artículo específico.

    Valida que el archivo descargado sea un PDF válido y lo guarda en el sistema de archivos.

    Args:
        session (aiohttp.ClientSession): Sesión HTTP.
        article (Article): Instancia del modelo de artículo.
        pdf_dir (Path): Directorio de destino.

    Returns:
        tuple[str, str, str]: (ID del artículo, Estado de descarga, Ruta del archivo).
    """
    url = article.open_access_url
    if not url:
        return article.id, DownloadStatus.NOT_FOUND.value, ""

    # Build filename
    first_author = (article.authors or "unknown").split(",")[0].strip().split()[-1]
    year = article.year or "nd"
    title_slug = _sanitize_filename(article.title)[:50]
    filename = f"{year}_{first_author}_{title_slug}.pdf"
    filepath = pdf_dir / filename

    # Skip if already downloaded
    if filepath.exists() and filepath.stat().st_size > 1000:
        return article.id, DownloadStatus.SUCCESS.value, str(filepath)

    async with _download_semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=settings.download_timeout)) as resp:
                if resp.status == 403 or resp.status == 401:
                    return article.id, DownloadStatus.PAYWALL.value, ""
                if resp.status != 200:
                    logger.warning("Download failed for %s: HTTP %d", article.doi, resp.status)
                    return article.id, DownloadStatus.FAILED.value, ""

                content = await resp.read()

                # Validate it's actually a PDF
                if not content[:4].startswith(PDF_MAGIC_BYTES):
                    logger.warning("Downloaded file for %s is not a PDF", article.doi)
                    return article.id, DownloadStatus.FAILED.value, ""

                filepath.write_bytes(content)
                logger.info("Downloaded: %s (%d bytes)", filename, len(content))
                return article.id, DownloadStatus.SUCCESS.value, str(filepath)

        except asyncio.TimeoutError:
            logger.warning("Download timeout for %s", article.doi)
            return article.id, DownloadStatus.FAILED.value, ""
        except Exception as e:
            logger.error("Download error for %s: %s", article.doi, str(e))
            return article.id, DownloadStatus.FAILED.value, ""


async def download_articles(
    db: AsyncSession,
    project_id: str,
    article_ids: list[str] | None = None,
) -> dict:
    """
    Orquesta la descarga de múltiples artículos dentro de un proyecto.

    Automáticamente dispara el pipeline de enriquecimiento tras cada descarga exitosa:
    Parseo → Análisis LLM → Indexación RAG.

    Args:
        db (AsyncSession): Sesión de base de datos.
        project_id (str): Identificador del proyecto.
        article_ids (list[str] | None): Lista opcional de artículos a descargar. Si es None, busca pendientes.

    Returns:
        dict: Resumen de resultados (total, descargados, fallidos, paywalls).
    """
    # Build query
    query = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )

    if article_ids:
        query = query.where(Article.id.in_(article_ids))
    else:
        query = query.where(
            Article.download_status == DownloadStatus.PENDING,
            Article.open_access_url.isnot(None),
        )

    result = await db.execute(query)
    articles = list(result.scalars().all())

    if not articles:
        return {
            "total": 0,
            "downloaded": 0,
            "failed": 0,
            "paywall": 0,
        }

    from app.models.project import Project, SearchQuery
    project = await db.get(Project, project_id)
    
    sq_query = select(SearchQuery).where(SearchQuery.project_id == project_id).order_by(SearchQuery.created_at.asc())
    sq_result = await db.execute(sq_query)
    search_queries = list(sq_result.scalars().all())
    sq_map = {sq.id: f"Busqueda_{idx}" for idx, sq in enumerate(search_queries, 1)}

    logger.info("Starting download of %d articles for project %s", len(articles), project_id)

    # Download in parallel (bounded by semaphore)
    async with aiohttp.ClientSession(
        headers={"User-Agent": "AgriSearch/0.1 (Academic Research Tool)"}
    ) as session:
        tasks = []
        for article in articles:
            search_name = sq_map.get(article.search_query_id, "Sin_Busqueda")
            pdf_dir = settings.get_project_pdfs_dir(project_id, project.name if project else None, search_name)
            tasks.append(_download_single_pdf(session, article, pdf_dir))
        
        results = await asyncio.gather(*tasks)

    # FINAL STEP: Automatically Update DB, Parse to MD and Analyze
    from app.services.pdf_parser import pdf_parser
    from app.services.llm_service import analyze_article_content
    from app.services.vector_service import VectorService
    import json
    
    vector_service = VectorService()

    status_counts = {
        "downloaded": 0,
        "failed": 0,
        "paywall": 0,
    }

    results_map = {article_id: (str(status), filepath) for article_id, status, filepath in results}

    for article in articles:
        new_status_record = results_map.get(article.id)
        if new_status_record:
            new_status, filepath = new_status_record
            article.download_status = new_status
            
            if new_status == DownloadStatus.SUCCESS.value:
                if filepath:
                    article.local_pdf_path = filepath

                status_counts["downloaded"] += 1
                try:
                    # 1. PDF -> MD (Sub-fase 2.0)
                    parsed_ok = await pdf_parser.parse_article(article, db)
                    
                    if parsed_ok and article.local_md_path:
                        # 2. MD -> LLM Analysis (Sub-fase 2.1)
                        with open(article.local_md_path, "r", encoding="utf-8") as f:
                            md_text = f.read()
                        
                        analysis = await analyze_article_content(
                            md_text, 
                            project_goal=project.description if project else ""
                        )
                        
                        article.llm_summary = analysis.get("llm_summary")
                        article.relevance_score = analysis.get("relevance_score", 0.0)
                        article.methodology_type = analysis.get("methodology_type")
                        
                        agri_vars = analysis.get("agri_variables", {})
                        article.agri_variables_json = json.dumps(agri_vars)
                        
                        # 3. RAG Indexing (Sub-fase 2.3)
                        await vector_service.index_article(
                            project_id=project_id,
                            article=article,
                            md_content=md_text
                        )
                        
                        logger.info(f"Auto-enriched and RAG-indexed article {article.id}.")
                except Exception as e:
                    logger.error(f"Post-download auto-processing failed for {article.id}: {e}")
            elif new_status == DownloadStatus.FAILED.value:
                status_counts["failed"] += 1
            elif new_status == DownloadStatus.PAYWALL.value:
                status_counts["paywall"] += 1

    await db.commit()
    # Refresh articles to get all DB fields correctly
    for article in articles:
        await db.refresh(article)

    return {
        "total": len(articles),
        **status_counts,
        "articles": articles
    }
