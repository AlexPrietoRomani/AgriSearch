"""
Archivo: search_service.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Servicio de orquestación de búsqueda bibliográfica multibase.
Coordina la ejecución de consultas en bases de datos científicas (OpenAlex, Semantic Scholar,
ArXiv, Crossref, CORE, SciELO, Redalyc, AgEcon Search, Organic Eprints),
consolida los resultados, realiza la desduplicación y persiste los registros vinculados a proyectos.

Acciones Principales:
    - Extracción de conceptos clave desde consultas en lenguaje natural.
    - Ejecución asíncrona y paralela de búsquedas en múltiples fuentes.
    - Desduplicación robusta basada en DOI y similitud difusa (Fuzzy) de títulos.
    - Gestión del ciclo de vida de las búsquedas (creación, paginación y eliminación).
    - Adaptación determinista de consultas según la base de datos objetivo.

Estructura Interna:
    - `execute_search`: Orquestador principal de la búsqueda y persistencia.
    - `_extract_concepts_from_query`: Procesa la entrada del usuario.
    - `_normalize_doi`: Estandariza DOIs para comparación.
    - `_is_duplicate_title`: Implementa RapidFuzz para detección de duplicados.

Entradas / Dependencias:
    - Clientes MCP para cada base de datos.
    - `QueryBuilder` para la adaptación sintáctica.
    - Base de datos (SQLAlchemy AsyncSession).

Salidas / Efectos:
    - Registra nuevas consultas (`SearchQuery`) y artículos (`Article`) en la DB.
    - Coordina llamadas de red paralelas a múltiples APIs externas.
    - Elimina archivos físicos (PDF/MD) al borrar consultas.

Ejemplo de Integración:
    results = await execute_search(db, project_id, "control biológico", ["arxiv", "scielo"])
"""

import asyncio
import logging
import re
import json
from datetime import datetime, timezone

from rapidfuzz import fuzz
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.project import Article, SearchQuery, Project
from app.services.mcp_clients.openalex_client import search_openalex
from app.services.mcp_clients.semantic_scholar_client import search_semantic_scholar
from app.services.mcp_clients.arxiv_client import search_arxiv
from app.services.mcp_clients.crossref_client import search_crossref
from app.services.mcp_clients.core_client import search_core
from app.services.mcp_clients.scielo_client import search_scielo
from app.services.mcp_clients.redalyc_client import search_redalyc
from app.services.mcp_clients.oaipmh_client import search_oaipmh
from app.services.query_builder import build_all_queries

logger = logging.getLogger(__name__)
settings = get_settings()

DOI_REGEX = re.compile(r"^10\.\d{4,}/\S+$")

# Common boolean/separator tokens to strip from queries (English and Spanish)
_QUERY_SEPARATORS = re.compile(r'\b(?:AND|OR|NOT|Y|O|E|U|NO)\b', re.IGNORECASE)
_CLEAN_RE = re.compile(r'[()"\[\]]')


def _extract_concepts_from_query(query: str) -> list[str]:
    """
    Extrae conceptos significativos de una cadena de consulta.

    Maneja tanto consultas booleanas legibles como descripciones en lenguaje natural.

    Args:
        query (str): Cadena de búsqueda cruda del usuario.

    Returns:
        list[str]: Lista de términos o frases conceptuales limpias.
    """
    if not query or not query.strip():
        return []

    # Remove boolean operators and parentheses, leaving multiple spaces for splitting
    cleaned = _QUERY_SEPARATORS.sub('  ', query)
    cleaned = _CLEAN_RE.sub(' ', cleaned)

    # Split by whitespace runs and rejoin meaningful phrases
    # A concept is a group of words between boolean operators
    # Split by whitespace runs (2 or more spaces) where operators once were
    raw_parts = [p.strip() for p in re.split(r'\s{2,}', cleaned) if p.strip()]

    # If splitting by double-spaces didn't work well, try single-space chunks
    if len(raw_parts) <= 1:
        raw_parts = [p.strip() for p in re.split(r'\s{2,}', cleaned) if p.strip()]

    # If still just one big blob, split by single spaces into reasonable chunks
    if len(raw_parts) <= 1:
        words = cleaned.split()
        # Group into phrases of 1-3 words
        raw_parts = []
        i = 0
        while i < len(words):
            # Try to identify multi-word concepts (2-3 words)
            if i + 2 < len(words):
                raw_parts.append(f"{words[i]} {words[i+1]} {words[i+2]}")
                i += 3
            elif i + 1 < len(words):
                raw_parts.append(f"{words[i]} {words[i+1]}")
                i += 2
            else:
                raw_parts.append(words[i])
                i += 1

    # Clean up and deduplicate
    concepts = []
    seen = set()
    for part in raw_parts:
        concept = part.strip().lower()
        if concept and concept not in seen and len(concept) > 1:
            concepts.append(part.strip())
            seen.add(concept)

    return concepts[:10]  # Cap at 10 concepts max


def _normalize_doi(doi: str | None) -> str | None:
    """
    Normaliza un DOI para permitir comparaciones precisas.

    Args:
        doi (str | None): DOI crudo.

    Returns:
        str | None: DOI normalizado (sin prefijos de URL) o None si es inválido.
    """
    if not doi:
        return None
    doi = doi.strip().lower()
    # Remove common prefixes
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi if DOI_REGEX.match(doi) else None


def _is_duplicate_title(title_a: str, title_b: str, threshold: float = 0.85) -> bool:
    """
    Verifica si dos títulos son duplicados mediante comparación difusa.

    Args:
        title_a (str): Primer título.
        title_b (str): Segundo título.
        threshold (float): Umbral de similitud (0.0 a 1.0).

    Returns:
        bool: True si la similitud supera el umbral.
    """
    if not title_a or not title_b:
        return False
    ratio = fuzz.ratio(title_a.lower().strip(), title_b.lower().strip()) / 100.0
    return ratio >= threshold


async def execute_search(
    db: AsyncSession,
    project_id: str,
    query: str,
    databases: list[str],
    max_results_per_source: int = 50,
    year_from: int | None = None,
    year_to: int | None = None,
    raw_prompt: str | None = None,
) -> dict:
    """
    Ejecuta una búsqueda en las bases de datos seleccionadas, desduplica y persiste resultados.

    Args:
        db (AsyncSession): Sesión de base de datos.
        project_id (str): ID del proyecto.
        query (str): Consulta booleana o descriptiva.
        databases (list[str]): Lista de fuentes a consultar.
        max_results_per_source (int): Límite de resultados por fuente.
        year_from (int | None): Año de inicio.
        year_to (int | None): Año de fin.
        raw_prompt (str | None): Prompt original que generó la consulta (opcional).

    Returns:
        dict: Resumen de la búsqueda con conteos por fuente y lista de artículos.
    """
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Store the search query
    search_query = SearchQuery(
        project_id=project_id,
        raw_input=raw_prompt or query,
        generated_query=query,
        databases_used=",".join(databases),
    )
    db.add(search_query)
    await db.flush()

    # ── Build deterministic queries for each DB ──
    concepts = _extract_concepts_from_query(query)
    adapted_queries = build_all_queries(concepts=concepts, databases=databases)
    search_query.adapted_queries_json = json.dumps(adapted_queries, ensure_ascii=False)
    await db.flush()

    logger.info("Concepts extracted: %s", concepts)
    logger.info("Adapted queries: %s", adapted_queries)

    # Execute searches in parallel using adapted queries
    tasks = []
    if "openalex" in databases:
        tasks.append(("openalex", search_openalex(adapted_queries["openalex"], max_results_per_source, year_from, year_to)))
    if "semantic_scholar" in databases:
        tasks.append(("semantic_scholar", search_semantic_scholar(adapted_queries["semantic_scholar"], max_results_per_source, year_from, year_to)))
    if "arxiv" in databases:
        tasks.append(("arxiv", search_arxiv(adapted_queries["arxiv"], max_results_per_source, year_from, year_to)))
    if "crossref" in databases:
        tasks.append(("crossref", search_crossref(adapted_queries["crossref"], max_results_per_source, year_from, year_to)))
    if "core" in databases:
        tasks.append(("core", search_core(adapted_queries["core"], max_results_per_source, year_from, year_to)))
    if "scielo" in databases:
        tasks.append(("scielo", search_scielo(adapted_queries["scielo"], max_results_per_source, year_from, year_to)))
    if "redalyc" in databases:
        tasks.append(("redalyc", search_redalyc(adapted_queries["redalyc"], max_results_per_source, year_from, year_to)))
    if "agecon" in databases:
        tasks.append(("agecon", search_oaipmh(adapted_queries["agecon"], source="agecon", max_results=max_results_per_source, year_from=year_from, year_to=year_to)))
    if "organic_eprints" in databases:
        tasks.append(("organic_eprints", search_oaipmh(adapted_queries["organic_eprints"], source="organic_eprints", max_results=max_results_per_source, year_from=year_from, year_to=year_to)))

    all_articles: list[dict] = []
    counts_by_source: dict[str, int] = {}

    results = await asyncio.gather(
        *[t[1] for t in tasks],
        return_exceptions=True,
    )

    for (source_name, _), result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error("Search failed for %s using query '%s': %s", source_name, adapted_queries.get(source_name), str(result))
            counts_by_source[source_name] = 0
            continue
        
        counts_by_source[source_name] = len(result)
        logger.info("[search] %s yielded %d raw results", source_name, len(result))
        for article_data in result:
            article_data["source_database"] = source_name
            all_articles.append(article_data)

    # ── Deduplication ──
    seen_dois: dict[str, int] = {}
    unique_articles: list[dict] = []
    duplicates_removed = 0

    for article_data in all_articles:
        normalized_doi = _normalize_doi(article_data.get("doi"))
        if normalized_doi and normalized_doi in seen_dois:
            duplicates_removed += 1
            continue
        if normalized_doi:
            seen_dois[normalized_doi] = len(unique_articles)
        unique_articles.append(article_data)

    # Fuzzy title dedup
    final_articles: list[dict] = []
    existing_titles: list[str] = []

    for article_data in unique_articles:
        title = article_data.get("title", "")
        is_dup = False
        for existing_title in existing_titles:
            if _is_duplicate_title(title, existing_title, settings.search_dedup_threshold):
                is_dup = True
                duplicates_removed += 1
                break
        if not is_dup:
            final_articles.append(article_data)
            existing_titles.append(title)

    # Cross-check against existing articles in the project
    existing_query = select(Article.doi, Article.title).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,
    )
    existing_result = await db.execute(existing_query)
    existing_rows = existing_result.all()
    existing_project_dois = {_normalize_doi(r.doi) for r in existing_rows if r.doi}
    existing_project_titles = [r.title for r in existing_rows if r.title]

    new_articles: list[dict] = []
    for article_data in final_articles:
        normalized_doi = _normalize_doi(article_data.get("doi"))
        if normalized_doi and normalized_doi in existing_project_dois:
            duplicates_removed += 1
            continue
        title = article_data.get("title", "")
        is_dup = False
        for et in existing_project_titles:
            if _is_duplicate_title(title, et, settings.search_dedup_threshold):
                is_dup = True
                duplicates_removed += 1
                break
        if not is_dup:
            new_articles.append(article_data)

    # ── Store in DB ──
    stored_articles: list[Article] = []
    for article_data in new_articles:
        article = Article(
            project_id=project_id,
            search_query_id=search_query.id,
            doi=article_data.get("doi"),
            title=article_data.get("title", "Unknown Title"),
            authors=article_data.get("authors"),
            year=article_data.get("year"),
            abstract=article_data.get("abstract"),
            journal=article_data.get("journal"),
            url=article_data.get("url"),
            keywords=article_data.get("keywords"),
            source_database=article_data.get("source_database", "unknown"),
            external_id=article_data.get("external_id"),
            open_access_url=article_data.get("open_access_url"),
            document_type=article_data.get("document_type", "journal-article"),
        )
        db.add(article)
        stored_articles.append(article)

    # Update search query stats
    search_query.total_results = len(new_articles)
    search_query.duplicates_removed = duplicates_removed

    await db.flush()

    logger.info(
        "Search complete: %d new articles stored, %d duplicates removed for project %s",
        len(new_articles),
        duplicates_removed,
        project_id,
    )

    return {
        "query_id": search_query.id,
        "total_found": len(new_articles),
        "duplicates_removed": duplicates_removed,
        "articles": stored_articles,
        "counts_by_source": counts_by_source,
        "adapted_queries": adapted_queries,
    }


async def get_project_articles(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 50,
    download_status: str | None = None,
    search_query_id: str | None = None,
) -> tuple[list[Article], int]:
    """
    Obtiene artículos paginados para un proyecto, con filtros opcionales.

    Args:
        db (AsyncSession): Sesión de base de datos.
        project_id (str): ID del proyecto.
        skip (int): Desplazamiento (offset).
        limit (int): Límite de resultados.
        download_status (str | None): Filtro por estado de descarga.
        search_query_id (str | None): Filtro por ID de consulta de búsqueda.

    Returns:
        tuple[list[Article], int]: Lista de artículos y conteo total.
    """
    base_query = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,
    )

    if download_status:
        base_query = base_query.where(Article.download_status == download_status)
    
    if search_query_id:
        base_query = base_query.where(Article.search_query_id == search_query_id)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated articles
    articles_query = base_query.order_by(Article.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(articles_query)
    articles = list(result.scalars().all())

    return articles, total


async def delete_search_query(
    db: AsyncSession,
    project_id: str,
    query_id: str,
):
    """
    Elimina una consulta de búsqueda y todos sus artículos asociados.

    También elimina los archivos PDF y Markdown locales vinculados a dichos artículos.

    Args:
        db (AsyncSession): Sesión de base de datos.
        project_id (str): ID del proyecto.
        query_id (str): ID de la consulta a eliminar.
    """
    import os
    import shutil
    
    # Verify the search query exists
    result = await db.execute(
        select(SearchQuery).where(
            SearchQuery.id == query_id, SearchQuery.project_id == project_id
        )
    )
    search_query = result.scalar_one_or_none()
    
    if not search_query:
        raise ValueError("Search Query not found.")
        
    # Get associated articles to locate PDF and MD files
    articles_result = await db.execute(
        select(Article.local_pdf_path, Article.local_md_path).where(
            Article.search_query_id == query_id,
            Article.project_id == project_id,
        )
    )
    file_pairs = articles_result.fetchall()
    
    # Delete PDF and MD files
    for pdf_path, md_path in file_pairs:
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            logger.warning(f"Failed to delete PDF {pdf_path}: {e}")
        try:
            if md_path and os.path.exists(md_path):
                os.remove(md_path)
        except Exception as e:
            logger.warning(f"Failed to delete MD {md_path}: {e}")
            
    # Delete the search query and explicitly delete the articles due to lack of relationship schema cascade.
    await db.execute(delete(Article).where(Article.search_query_id == query_id))
    await db.delete(search_query)
    await db.commit()
