"""
AgriSearch Backend - PDF to Structured Markdown Parser (Docling-based).
Implements Sub-fase 2.0: PDF -> Enriched Markdown.
"""

import os
import re
import yaml
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.project import Article, Project
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class TableFlattener:
    """Transforms Markdown tables into descriptive natural language sentences."""

    _TABLE_PATTERN = re.compile(r"((?:^\|.+\|$\n?)+)", re.MULTILINE)

    @staticmethod
    def _parse_table_block(table_text: str) -> tuple:
        lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return [], []

        # Headers
        headers = [cell.strip() for cell in lines[0].split("|") if cell.strip()]
        
        # Rows (skip header and separator)
        rows = []
        for line in lines[2:]:
            if re.match(r"^\|[\s\-:]+\|$", line):
                continue
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if cells:
                rows.append(cells)
        return headers, rows

    @classmethod
    def flatten(cls, md_text: str, doc_meta: Optional[Dict[str, Any]] = None) -> str:
        doc_meta = doc_meta or {}
        doc_title = doc_meta.get("title", "Documento")
        doc_year = doc_meta.get("year", "")

        def _replace_table(match):
            table_text = match.group(0)
            headers, rows = cls._parse_table_block(table_text)
            if not headers or not rows:
                return table_text

            sentences = []
            for row in rows:
                pairs = []
                for i, cell in enumerate(row):
                    if i < len(headers) and cell and cell != "-":
                        pairs.append(f"{headers[i]}: {cell}")
                if pairs:
                    prefix = f"Según {doc_title}"
                    if doc_year:
                        prefix += f" ({doc_year})"
                    sentences.append(f"{prefix}, {', '.join(pairs)}.")
            return "\n".join(sentences) if sentences else table_text

        return cls._TABLE_PATTERN.sub(_replace_table, md_text)


class PDFParserService:
    """PDF to Markdown parser using IBM's Docling."""

    def __init__(self):
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.pipeline_options import PdfPipelineOptions
                
                options = PdfPipelineOptions()
                options.do_table_structure = True
                options.do_formula_enrichment = True
                options.do_ocr = True  # Enable OCR for scanned PDFs
                
                self._converter = DocumentConverter(
                    format_options={
                        "pdf": PdfFormatOption(pipeline_options=options)
                    }
                )
                logger.info("Docling DocumentConverter initialized successfully.")
            except ImportError as e:
                logger.error(f"Docling dependencies missing: {e}")
                raise
        return self._converter

    async def parse_article(self, article: Article, db: Session) -> bool:
        """Parses an article PDF to enriched Markdown and updates the DB."""
        if not article.local_pdf_path or not os.path.exists(article.local_pdf_path):
            logger.warning(f"No PDF found for article {article.id}")
            article.parsed_status = "failed"
            db.commit()
            return False

        try:
            pdf_path = Path(article.local_pdf_path)
            project_id = article.project_id
            
            # 1. Define output path
            parsed_dir = settings.get_project_parsed_dir(project_id)
            
            sanitize_title = re.sub(r'[^\w\s-]', '', article.title[:50]).strip().replace(' ', '_')
            output_path = parsed_dir / f"{article.id}_{sanitize_title}.md"

            # 2. Convert PDF to Markdown (Offload to thread to avoid blocking)
            loop = asyncio.get_event_loop()
            md_content = await loop.run_in_executor(None, self._convert_to_md, str(pdf_path))

            # 3. Apply Table Flattening
            meta = {"title": article.title, "year": article.year}
            enriched_md = TableFlattener.flatten(md_content, meta)

            # 4. Add YAML Front-matter
            front_matter = {
                "agrisearch_id": article.id,
                "doi": article.doi,
                "title": article.title,
                "authors": article.authors,
                "year": article.year,
                "journal": article.journal,
                "keywords": article.keywords.split(",") if article.keywords else [],
                "source_database": article.source_database
            }
            
            final_content = "---\n" + yaml.dump(front_matter, sort_keys=False) + "---\n\n" + enriched_md

            # 5. Save file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_content)

            # 6. Update Article record
            article.local_md_path = str(output_path)
            article.parsed_status = "success"
            db.commit()
            
            logger.info(f"Successfully parsed article {article.id} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to parse article {article.id}: {e}")
            article.parsed_status = "failed"
            db.commit()
            return False

    def _convert_to_md(self, pdf_path: str) -> str:
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        return result.document.export_to_markdown()

# Global instance
pdf_parser = PDFParserService()
