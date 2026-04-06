"""
AgriSearch Backend - PDF Processing and Enrichment Service.

Coordinates the conversion of PDFs to structured Markdown using Docling,
and extracts/updates bibliographic metadata for better screening and RAG.
"""

import logging
import re
from pathlib import Path

from app.services.document_parser_service import DoclingParser, ImageFilter
from app.services.summarization_service import SummarizationService
from app.services.vector_service import VectorService
from app.models.project import Article, DownloadStatus
from app.core.config import get_settings

logger = logging.getLogger(__name__)

def scan_and_match_pdfs(pdf_dir: Path, articles: list) -> dict[str, str]:
    """
    Scan a PDF directory and try to match files to articles by DOI or title fragments.
    Returns a dict of {article_id: pdf_path_string}.
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


async def process_and_enrich_pdf(db, article: Article, parser: DoclingParser, vector_service: VectorService, vlm: ImageFilter = None) -> bool:
    """
    Processes a single article:
    1. Converts PDF to Markdown (via Docling).
    2. Saves Markdown to disk.
    3. Updates article model with Markdown path and status.
    4. Extracts basic metadata (abstract/keywords) if missing.
    """
    if not article.local_pdf_path or not Path(article.local_pdf_path).exists():
        logger.warning(f"No PDF path found for article {article.id}")
        return False

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

        # 1. Parse PDF using Docling
        final_md = await parser.parse_pdf(pdf_path, meta, vlm_describer=vlm)

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
        
        # 5. Generate Enriched Summary (Optional but recommended)
        try:
            summary_json = await SummarizationService.generate_summary(final_md)
            article.enriched_summary = SummarizationService.format_summary_to_markdown(summary_json)
        except Exception as es:
            logger.warning(f"Summarization failed for {article.id[:8]}: {es}")

        # 6. Index in Qdrant (Vector RAG)
        try:
            vector_service = vector_service  # Use the passed instance
            await vector_service.index_article(
                project_id=article.project_id, 
                article_id=article.id, 
                title=article.title, 
                md_content=final_md
            )
        except Exception as ev:
            logger.warning(f"Vector indexing failed for {article.id[:8]}: {ev}")

        logger.info(f"Processed, Summarized and Indexed article {article.id[:8]} -> {md_path.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to process PDF for {article.id[:8]}: {e}")
        return False


async def enrich_articles_from_pdfs(db, project_id: str, article_ids: list[str] | None = None) -> dict:
    """
    High-fidelity enrichment using Docling.
    """
    from sqlalchemy import select
    from app.core.config import get_settings

    settings = get_settings()
    pdf_dir = settings.get_project_pdfs_dir(project_id)
    
    # Initialize Services
    try:
        parser = DoclingParser()
        vector_service = VectorService()
        vlm = None 
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
        # Only process those that have a PDF but aren't parsed yet
        stmt = stmt.where(Article.local_pdf_path.isnot(None), Article.parsed_status == 'pending')

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    if not articles:
        return {"total": 0, "processed": 0}

    stats = {
        "total": len(articles),
        "processed": 0,
        "failed": 0
    }

    for article in articles:
        success = await process_and_enrich_pdf(db, article, parser, vector_service, vlm)
        if success:
            stats["processed"] += 1
        else:
            stats["failed"] += 1
    
    await db.commit()
    return stats
