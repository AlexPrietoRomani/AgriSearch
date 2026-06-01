"""
Archivo: pdf_enrichment_service.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Servicio encargado de la orquestación del procesamiento y enriquecimiento de PDFs.
Coordina la conversión de archivos PDF a Markdown estructurado y extrae metadatos bibliográficos
faltantes (abstracts, keywords) para optimizar el cribado y la recuperación RAG.

Acciones Principales:
    - Escaneo y emparejamiento de archivos PDF locales con registros de la base de datos.
    - Conversión masiva de documentos usando el motor de ruteo dual (OpenDataLoader/MarkItDown).
    - Extracción de secciones de resumen (Abstract) directamente del contenido parseado.
    - Publicación de eventos de progreso en tiempo real para la interfaz de usuario.
    - Gestión de cancelación de tareas de procesamiento por proyecto.

Estructura Interna:
    - `scan_and_match_pdfs`: Algoritmo de emparejamiento por DOI y fragmentos de título.
    - `process_and_enrich_pdf`: Pipeline individual para un artículo (Parseo -> MD -> Metadatos).
    - `enrich_articles_from_pdfs`: Orquestador de procesamiento por lotes para un proyecto.

Entradas / Dependencias:
    - Motores de parseo (`OpenDataLoaderParser`, `MarkItDownParser`).
    - Base de datos (SQLAlchemy AsyncSession).
    - Sistema de eventos SSE.

Ejemplo de Integración:
    stats = await enrich_articles_from_pdfs(db, project_id)
"""

import logging
import re
import asyncio
from pathlib import Path
from typing import Set

# Registro de cancelaciones: project_id -> bool
_cancelled_projects: Set[str] = set()


def cancel_enrichment(project_id: str):
    """
    Marca una tarea de enriquecimiento de proyecto como cancelada.

    Args:
        project_id (str): ID del proyecto a cancelar.
    """
    _cancelled_projects.add(project_id)


def is_cancelled(project_id: str) -> bool:
    """
    Verifica si el enriquecimiento del proyecto fue cancelado.

    Args:
        project_id (str): ID del proyecto a verificar.

    Returns:
        bool: True si fue cancelado, False en caso contrario.
    """
    if project_id in _cancelled_projects:
        _cancelled_projects.remove(project_id)
        return True
    return False


from app.services.summarization_service import SummarizationService
from app.services.vector_service import VectorService
from app.models.project import Article, DownloadStatus
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def scan_and_match_pdfs(pdf_dir: Path, articles: list) -> dict[str, str]:
    """
    Escanea un directorio de PDFs e intenta emparejarlos con artículos existentes.

    Utiliza una estrategia de búsqueda por DOI en el nombre y, opcionalmente, 
    fragmentos de autor y año.

    Args:
        pdf_dir (Path): Directorio que contiene los archivos PDF crudos.
        articles (list): Lista de instancias del modelo Article.

    Returns:
        dict[str, str]: Mapeo de {article_id: ruta_absoluta_pdf}.
    """
    if not pdf_dir.exists():
        return {}

    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return {}

    matched = {}
    for article in articles:
        if article.local_pdf_path and Path(article.local_pdf_path).exists():
            matched[article.id] = article.local_pdf_path
            continue

        # Try matching by DOI in filename
        if article.doi:
            doi_safe = re.sub(r'[/<>:"/\\|?*]', '_', article.doi)
            for pdf_file in pdf_files:
                if doi_safe in pdf_file.name:
                    matched[article.id] = str(pdf_file)
                    break

        # Try matching by author/year pattern
        if article.id not in matched:
            first_author = (article.authors or "").split(",")[0].strip().split()[-1] if article.authors else ""
            year = str(article.year) if article.year else ""
            if first_author and year:
                for pdf_file in pdf_files:
                    if year in pdf_file.name and first_author.lower() in pdf_file.name.lower():
                        matched[article.id] = str(pdf_file)
                        break

    return matched


async def process_and_enrich_pdf(db, article: Article, parsers: dict, publish_event = None, project_id: str = None) -> bool:
    """
    Procesa un único artículo: conversión a Markdown y extracción de metadatos básicos.

    Flujo:
    1. Convierte PDF a Markdown mediante el ruteador de parsers duales.
    2. Guarda el Markdown resultante en disco.
    3. Actualiza el modelo del artículo con la ruta del MD y el estado de calidad.
    4. Intenta extraer el resumen (Abstract) si falta, usando expresiones regulares sobre el MD.

    Args:
        db: Sesión de base de datos.
        article (Article): Artículo a procesar.
        parsers (dict): Diccionario con instancias de parsers inicializados.
        publish_event (callable): Función para notificar progreso.
        project_id (str): ID del proyecto para eventos.

    Returns:
        dict: Resultado con clave 'success' y detalles de calidad.
    """
    if not article.local_pdf_path or not Path(article.local_pdf_path).exists():
        logger.warning(f"No PDF path found for article {article.id}")
        return {"success": False, "error": "no_pdf_path"}

    pdf_path = Path(article.local_pdf_path)
    # Target Markdown path
    md_path = pdf_path.with_suffix(".md")
    
    try:
        # Prepare metadata for YAML front-matter
        meta = {
            "id": article.id,
            "doi": article.doi,
            "title": article.title,
            "authors": article.authors,
            "year": article.year,
            "journal": article.journal,
            "keywords": (article.keywords or "").split(","),
            "source_database": article.source_database
        }

        from app.services.document_parser_service import ParserRouter
        
        # RUTEO: Seleccionar parser según tipo de archivo y fuente científica
        selected_parser, engine = ParserRouter.select_parser(
            file_path=pdf_path,
            article_meta=meta,
            opendataloader_parser=parsers.get("opendataloader"),
            markitdown_parser=parsers.get("markitdown"),
        )
        
        try:
            parse_coro = selected_parser.parse_document(pdf_path, meta, publish_event=publish_event, project_id=project_id)
            final_md = await asyncio.wait_for(parse_coro, timeout=1800.0)
        except asyncio.TimeoutError:
            logger.error(f"Timeout procesando {article.id[:8]} ({pdf_path.name})")
            article.parsed_status = "timeout"
            return {"success": False, "error": "timeout"}

        # 2. Extract abstract if missing (from the generated MD)
        # Simple extraction: look for # Abstract or similar
        if not article.abstract or len(article.abstract) < 100:
            # Try to find a section that's probably the abstract
            abs_match = re.search(r'(?i)#+\s*(?:Abstract|Resumen|Summary)\s*\n+(.*?)(?=\n\s*(?:#|Keywords|Palabras))', final_md, re.DOTALL)
            if abs_match:
                article.abstract = abs_match.group(1).strip()[:3000]

        # 3. Save Markdown to disk
        md_path.write_text(final_md, encoding="utf-8")
        
        # 4. Update Article Record
        article.local_md_path = str(md_path)
        article.parsed_status = 'success'
        
        quality = "alta" if len(final_md) > 10000 else "media" if len(final_md) > 2000 else "baja"
        article.parsed_status = f"success_{quality}"

        logger.info(f"Processed article {article.id[:8]} -> {md_path.name} ({quality})")
        return {"success": True, "quality": quality, "md_len": len(final_md)}

    except Exception as e:
        logger.error(f"Failed to process PDF for {article.id[:8]}: {e}")
        return {"success": False, "error": str(e)}


async def enrich_articles_from_pdfs(db, project_id: str, article_ids: list[str] | None = None, force_reparse: bool = False) -> dict:
    """
    Realiza el enriquecimiento masivo de artículos mediante el pipeline Dual-Parser.

    Encamina artículos científicos hacia OpenDataLoader y documentos generales hacia MarkItDown.

    Args:
        db: Sesión de base de datos.
        project_id (str): Identificador del proyecto.
        article_ids (list[str] | None): Lista específica de artículos a procesar.
        force_reparse (bool): Si True, vuelve a parsear artículos ya marcados como 'success'.

    Returns:
        dict: Estadísticas del proceso (total, procesados, fallidos, métricas de calidad).
    """
    from sqlalchemy import select
    from app.core.config import get_settings
    from app.models.project import Project

    settings = get_settings()
    pdf_dir = settings.get_project_pdfs_dir(project_id)
    
    project = await db.get(Project, project_id)
    if not project:
        return {"error": "Proyecto no encontrado"}

    # Initialize Services
    try:
        from app.services.document_parser_service import (
            OpenDataLoaderParser, MarkItDownParser, OPENDATALOADER_AVAILABLE
        )
        
        # Inicializar ambos parsers
        parsers = {}
        
        if OPENDATALOADER_AVAILABLE:
            parsers["opendataloader"] = OpenDataLoaderParser()
            logger.info("StrataReaderParser inicializado (Rust+CPU) para PDFs científicos")
        else:
            logger.warning("Strata Reader no disponible. Todos los PDFs irán a MarkItDown.")
        
        # Configurar VLM via Ollama
        vlm_model = project.llm_model or settings.litellm_model
        if vlm_model and vlm_model.startswith("ollama/"):
            vlm_model = vlm_model.replace("ollama/", "")
        
        ollama_url = "http://localhost:11434/v1"
        parsers["markitdown"] = MarkItDownParser(llm_client=ollama_url, llm_model=vlm_model)
        logger.info(f"MarkItDownParser inicializado (CPU) | VLM: {'activo' if vlm_model else 'inactivo'}")
    except Exception as e:
        logger.error(f"Could not initialize Services: {e}")
        return {"error": str(e)}

    # Fetch articles
    stmt = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,
    )
    if article_ids:
        stmt = stmt.where(Article.id.in_(article_ids))
    else:
        # Only process those that have a PDF
        stmt = stmt.where(Article.local_pdf_path.isnot(None))
        if not force_reparse:
            # If not forcing, only process pending ones
            stmt = stmt.where(Article.parsed_status == 'pending')

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    if not articles:
        return {"total": 0, "processed": 0}

    stats = {
        "total": len(articles),
        "processed": 0,
        "failed": 0,
        "quality_metrics": {"alta": 0, "media": 0, "baja": 0}
    }

    from app.api.v1.events import publish_event
    
    for idx, article in enumerate(articles):
        if is_cancelled(project_id):
            logger.info(f"Enrichment cancelled for project {project_id}")
            await publish_event(project_id, {
                "type": "error",
                "msg": "Proceso detenido por el usuario."
            })
            break

        await publish_event(project_id, {
            "type": "progress",
            "article": article.title,
            "current": idx + 1,
            "total": len(articles)
        })
        res = await process_and_enrich_pdf(db, article, parsers, publish_event, project_id)
        
        # No se requiere GC manual con MarkItDown

        if res.get("success"):
            stats["processed"] += 1
            stats["quality_metrics"][res["quality"]] += 1
        else:
            stats["failed"] += 1
    
    await db.commit()
    return stats
