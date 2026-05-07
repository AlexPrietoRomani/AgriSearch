"""
Archivo: pdf_parser.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Servicio de parseo de PDF a Markdown estructurado basado en Docling (Legacy).
Implementa la Sub-fase 2.0 del pipeline: PDF -> Enriched Markdown.
Nota: Este servicio está siendo reemplazado por la arquitectura de ruteo dual,
pero se mantiene para flujos que requieren enriquecimiento visual directo con VLM.

Acciones Principales:
    - Conversión de PDF a Markdown manteniendo la estructura jerárquica.
    - Extracción de imágenes y diagramas para su análisis con modelos de visión.
    - Aplanamiento de tablas para optimizar la fragmentación en RAG.
    - Inyección de metadatos en Front-matter YAML.

Estructura Interna:
    - `TableFlattener`: Transforma tablas Markdown en oraciones narrativas.
    - `PDFParserService`: Clase principal que envuelve el motor Docling.
    - `_convert_to_md_with_vision`: Pipeline que integra visión artificial en el parseo.

Entradas / Dependencias:
    - Librería `docling`.
    - `llm_service` para descripciones de imágenes.
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
    """
    Utilidad para transformar tablas Markdown en oraciones de lenguaje natural.
    Ayuda a que los modelos de embeddings capturen mejor la relación entre celdas y encabezados.
    """

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
    """
    Servicio que implementa el parseo de PDFs científicos utilizando el motor Docling de IBM.
    """

    def __init__(self):
        """Inicializa el servicio sin cargar el motor (carga diferida)."""
        self._converter = None

    def _get_converter(self):
        """
        Carga e inicializa el DocumentConverter de Docling bajo demanda.
        
        Returns:
            DocumentConverter: Instancia configurada del motor de parseo.
        """
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

    async def _convert_to_md_with_vision(self, pdf_path: str, context: str = "") -> str:
        """
        Pipeline que integra la conversión de Docling con análisis visual de modelos LLM.

        Args:
            pdf_path (str): Ruta al PDF.
            context (str): Contexto para guiar la descripción de imágenes.

        Returns:
            str: Markdown con descripciones de imágenes inyectadas.
        """
        from docling.document_converter import DocumentConverter
        import base64
        from io import BytesIO
        from PIL import Image
        from app.services.llm_service import describe_image_content
        
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        
        # 1. Base Markdown from Docling
        md_text = result.document.export_to_markdown()
        
        # 2. Extract Pictures and Describe with Gemma 4 Vision
        # Docling stores pictures in result.document.pictures
        if hasattr(result.document, 'pictures') and result.document.pictures:
            logger.info(f"Analyzing {len(result.document.pictures)} images in {pdf_path}")
            
            for i, picture in enumerate(result.document.pictures):
                try:
                    # In Docling, picture.image might be a PIL Image or similar
                    img = picture.image
                    if img:
                        # Convert PIL to base64
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        description = await describe_image_content(img_str, context=context)
                        
                        # Replace image placeholder in MD with description
                        # Usually Docling marks images as <!-- [picture or figure] --> or similar
                        # We append descriptions to a list or inject them
                        md_text += f"\n\n### Figure Analysis {i+1}\n{description}\n"
                except Exception as e:
                    logger.warning(f"Failed to process image {i} in {pdf_path}: {e}")
        
        return md_text

    async def parse_article(self, article: Article, db: Session) -> bool:
        """
        Parse un PDF de artículo, lo convierte a MD enriquecido y actualiza la base de datos.

        Args:
            article (Article): Instancia del artículo.
            db (Session): Sesión de base de datos.

        Returns:
            bool: True si el proceso fue exitoso.
        """
        if not article.local_pdf_path or not os.path.exists(article.local_pdf_path):
            logger.warning(f"No PDF found for article {article.id}")
            article.parsed_status = "failed"
            await db.commit()
            return False

        try:
            pdf_path = Path(article.local_pdf_path)
            project_id = article.project_id
            
            # 1. Define output path
            parsed_dir = settings.get_project_parsed_dir(project_id)
            
            sanitize_title = re.sub(r'[^\w\s-]', '', article.title[:50]).strip().replace(' ', '_')
            output_path = parsed_dir / f"{article.id}_{sanitize_title}.md"

            # 2. Convert PDF to Markdown WITH VISION (Offload to thread for Docling part)
            # Since Vision is async, we call it directly
            md_content = await self._convert_to_md_with_vision(str(pdf_path), context=article.title)

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
            logger.info(f"Successfully parsed article {article.id} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to parse article {article.id}: {e}")
            article.parsed_status = "failed"
            db.commit()
            return False


# Global instance
pdf_parser = PDFParserService()
