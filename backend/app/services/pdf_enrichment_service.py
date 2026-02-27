"""
AgriSearch Backend - PDF Enrichment Service.

Reads downloaded PDFs to extract abstract, keywords, and update article metadata.
Used during screening session creation to fill in missing data.
"""

import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_abstract_from_pdf(pdf_path: str | Path) -> str | None:
    """
    Extract the abstract section from a PDF file.

    Looks for common patterns like 'Abstract', 'ABSTRACT', 'Resumen', 'Summary'
    and extracts the text that follows until the next section heading.
    """
    try:
        doc = fitz.open(str(pdf_path))
        # Extract text from first 3 pages (abstract is almost always there)
        pages_text = ""
        for page_num in range(min(3, len(doc))):
            pages_text += doc[page_num].get_text()
        doc.close()

        if not pages_text.strip():
            return None

        # Try to find abstract section with regex
        abstract_patterns = [
            r'(?i)\b(?:abstract|resumen|summary|résumé)\s*[\n:.\-—]+\s*(.*?)(?=\n\s*(?:keywords?|palabras\s*clave|introduction|introducción|1\.\s|key\s*words|index\s*terms|highlights|graphical\s*abstract|mots[\-\s]clés)\b)',
            r'(?i)\b(?:abstract|resumen|summary)\s*\n{1,3}(.*?)(?=\n\s*(?:keywords?|palabras\s*clave|introduction|introducción|1\.\s|key\s*words|index\s*terms|©|doi[\s:])\b)',
            # Fallback: just find "Abstract" and grab the next paragraph
            r'(?i)\b(?:abstract|resumen)\s*[:\n]\s*((?:(?!\n\s*\n).)*)',
        ]

        for pattern in abstract_patterns:
            match = re.search(pattern, pages_text, re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up: remove excessive whitespace, newlines
                abstract = re.sub(r'\s+', ' ', abstract)
                # Minimum length check (at least 100 chars for a real abstract)
                if len(abstract) >= 100:
                    # Maximum length cap (3000 chars, very long abstracts are likely mis-parsed)
                    return abstract[:3000]

        # Ultimate fallback: the first long continuous paragraph (at least 300 chars) that doesn't look like an author list
        paragraphs = re.split(r'\n\s*\n', pages_text)
        for p in paragraphs:
            cleaned = re.sub(r'\s+', ' ', p).strip()
            # If the paragraph has decent length and not too many commas/numbers (which indicate author list/affiliations)
            if len(cleaned) > 250 and len(cleaned) < 3000:
                if cleaned.count(',') < len(cleaned) / 20 and not re.match(r'^[\d\s\,\.\w]+$', p):
                    return cleaned

        # Better than nothing: just return the first 1500 characters of clean text
        clean_text = re.sub(r'\s+', ' ', pages_text).strip()
        if len(clean_text) > 100:
            return clean_text[:1500] + "..."

        return None

    except Exception as e:
        logger.warning("Failed to extract abstract from %s: %s", pdf_path, e)
        return None


def extract_keywords_from_pdf(pdf_path: str | Path) -> str | None:
    """
    Extract keywords from a PDF file.

    Looks for 'Keywords:', 'Palabras clave:', 'Index Terms:' etc.
    """
    try:
        doc = fitz.open(str(pdf_path))
        pages_text = ""
        for page_num in range(min(3, len(doc))):
            pages_text += doc[page_num].get_text()
        doc.close()

        if not pages_text.strip():
            return None

        keyword_patterns = [
            r'(?i)\b(?:keywords?|palabras\s*clave|key\s*words|index\s*terms|mots[\-\s]clés)\s*[:\-—]\s*(.*?)(?=\n\s*\n|\n\s*(?:1\.\s|introduction|introducción|abstract|resumen|©|doi[\s:]))',
        ]

        for pattern in keyword_patterns:
            match = re.search(pattern, pages_text, re.DOTALL)
            if match:
                keywords = match.group(1).strip()
                keywords = re.sub(r'\s+', ' ', keywords)
                # Remove trailing period
                keywords = keywords.rstrip('.')
                if len(keywords) > 5 and len(keywords) < 500:
                    return keywords

        return None

    except Exception as e:
        logger.warning("Failed to extract keywords from %s: %s", pdf_path, e)
        return None


def scan_and_match_pdfs(pdf_dir: Path, articles: list) -> dict[str, str]:
    """
    Scan a PDF directory and try to match files to articles by DOI or title fragments.

    Returns a dict of {article_id: pdf_filename}.
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


async def enrich_articles_from_pdfs(db, project_id: str, article_ids: list[str] | None = None) -> dict:
    """
    Enrich articles with data extracted from their PDFs.

    For each article with a downloaded PDF:
    1. Update local_pdf_path if missing
    2. Extract abstract if missing
    3. Extract keywords if missing

    Returns a summary of enrichment results.
    """
    from sqlalchemy import select
    from app.models.project import Article, DownloadStatus
    from app.core.config import get_settings

    settings = get_settings()
    pdf_dir = settings.get_project_pdfs_dir(project_id)

    # Fetch articles
    stmt = select(Article).where(
        Article.project_id == project_id,
        Article.is_duplicate == False,  # noqa: E712
    )
    if article_ids:
        stmt = stmt.where(Article.id.in_(article_ids))

    result = await db.execute(stmt)
    articles = list(result.scalars().all())

    if not articles:
        return {"total": 0, "pdfs_matched": 0, "abstracts_extracted": 0, "keywords_extracted": 0}

    # Step 1: Match PDFs to articles
    pdf_matches = scan_and_match_pdfs(pdf_dir, articles)

    stats = {
        "total": len(articles),
        "pdfs_matched": 0,
        "abstracts_extracted": 0,
        "keywords_extracted": 0,
        "paths_updated": 0,
    }

    for article in articles:
        changed = False
        pdf_path = pdf_matches.get(article.id)

        # Update local_pdf_path if we found a match
        if pdf_path and (not article.local_pdf_path or not Path(article.local_pdf_path).exists()):
            article.local_pdf_path = pdf_path
            article.download_status = DownloadStatus.SUCCESS
            stats["paths_updated"] += 1
            changed = True

        actual_path = pdf_path or article.local_pdf_path
        if not actual_path or not Path(actual_path).exists():
            continue

        stats["pdfs_matched"] += 1

        # Try to extract abstract from PDF and overwrite if it's better
        new_abstract = extract_abstract_from_pdf(actual_path)
        if new_abstract:
            old_abstract = article.abstract or ""
            # If current abstract is missing, or very short (less than 250 chars), or the new one is significantly longer
            if not article.abstract or len(old_abstract) < 250 or len(new_abstract) > len(old_abstract) + 100:
                article.abstract = new_abstract
                stats["abstracts_extracted"] += 1
                changed = True
                logger.info("Updated abstract for article %s (new length: %d)", article.id[:8], len(new_abstract))

        # Extract keywords if missing
        if not article.keywords or article.keywords.strip() == "":
            keywords = extract_keywords_from_pdf(actual_path)
            if keywords:
                article.keywords = keywords
                stats["keywords_extracted"] += 1
                changed = True
                logger.info("Extracted keywords for article %s: %s", article.id[:8], keywords[:80])

    await db.flush()

    logger.info(
        "Enrichment complete for project %s: %d articles, %d PDFs matched, %d abstracts, %d keywords",
        project_id[:8], stats["total"], stats["pdfs_matched"],
        stats["abstracts_extracted"], stats["keywords_extracted"],
    )

    return stats
