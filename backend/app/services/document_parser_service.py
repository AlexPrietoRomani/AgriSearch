"""
AgriSearch Backend - Document Parser Service.

Handles advanced PDF to Markdown conversion using Docling, 
table flattening for RAG optimization, and VLM-based image descriptions.
"""

import logging
import re
import yaml
import io
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import torch
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice, TableStructureOptions, TableFormerMode
    from docling.datamodel.base_models import InputFormat
    from docling_core.types.doc import ImageRefMode
    DOCLING_AVAILABLE = True
except ImportError:
    DocumentConverter = None
    PdfFormatOption = None
    PdfPipelineOptions = None
    AcceleratorOptions = None
    AcceleratorDevice = None
    TableStructureOptions = None
    TableFormerMode = None
    InputFormat = None
    ImageRefMode = None
    DOCLING_AVAILABLE = False

logger = logging.getLogger(__name__)

class TableFlattener:
    """
    Transforms Markdown tables into natural language sentences.
    Each row becomes a sentence referencing its headers to preserve context.
    """
    # Regex to detect Markdown table blocks
    _TABLE_PATTERN = re.compile(
        r"((?:^\|.+\|$\n?)+)",
        re.MULTILINE
    )

    @staticmethod
    def _parse_table_block(table_text: str) -> tuple:
        """Extracts headers and rows from a Markdown table block."""
        lines = [
            line.strip()
            for line in table_text.strip().split("\n")
            if line.strip()
        ]

        if len(lines) < 2:
            return [], []

        # Headers: first line
        headers = [
            cell.strip()
            for cell in lines[0].split("|")
            if cell.strip()
        ]

        # Rows: skip header + separator line
        rows = []
        for line in lines[2:]:
            # Validate row is not a separator
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            cells = [
                cell.strip()
                for cell in line.split("|")
                if cell.strip()
            ]
            if cells:
                # Ensure cells match header count or pad
                rows.append(cells)

        return headers, rows

    @classmethod
    def flatten(cls, md_text: str, doc_meta: Optional[Dict[str, Any]] = None) -> str:
        """Replaces tables in Markdown with descriptive sentences."""
        doc_meta = doc_meta or {}
        doc_title = doc_meta.get("title", "documento")
        doc_authors = doc_meta.get("authors", "").split(",")[0].strip() or "el autor"
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
                    if i < len(headers) and cell and cell not in ["-", "", "None"]:
                        pairs.append(f"{headers[i]}: {cell}")

                if pairs:
                    author_str = f"{doc_authors}"
                    if doc_year:
                        author_str += f" ({doc_year})"
                    
                    sentence = f"Según {author_str} en {doc_title}, se registra: {', '.join(pairs)}."
                    sentences.append(sentence)

            return "\n\n" + "\n".join(sentences) + "\n\n" if sentences else table_text

        return cls._TABLE_PATTERN.sub(_replace_table, md_text)


class ImageFilter:
    """
    Filters decorative images and describes technical ones using a VLM.
    """
    SYSTEM_PROMPT = (
        "Eres un analista experto en extracción de datos científicos. "
        "Describe en un único párrafo corto y directo qué representa esta imagen "
        "(ej: 'Gráfico de barras mostrando la relación entre X e Y'). "
        "Si la imagen es un logo, publicidad, decorativa o ilegible, "
        "responde ÚNICAMENTE con la palabra: DESCARTAR."
    )

    def __init__(self, model_name: str = "llama3.2-vision"):
        self.model = model_name

    async def analyze_image_bytes(self, image_bytes: bytes) -> Optional[str]:
        """Calls a VLM (via Ollama or similar) to describe image content."""
        # Note: Implementation depends on available local LLM provider (Ollama recommended)
        try:
            import ollama
            client = ollama.AsyncClient()
            response = await client.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": self.SYSTEM_PROMPT,
                    "images": [image_bytes]
                }],
                options={"temperature": 0.0}
            )
            text = response['message']['content'].strip()
            if "DESCARTAR" in text.upper() or len(text) < 10:
                return None
            return text
        except Exception as e:
            logger.warning(f"VLM analysis failed: {e}")
            return None


class DoclingParser:
    """
    Advanced PDF to Markdown converter using Docling.
    """
    def __init__(self):
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling is not installed. Please check requirements.txt.")
        
        # Configure Pipeline (Optimized for Memory)
        options = PdfPipelineOptions()
        options.do_table_structure = True
        options.table_structure_options = TableStructureOptions(
            do_cell_matching=True,
            mode=TableFormerMode.FAST # Changed from ACCURATE to FAST to save memory
        )
        options.do_formula_enrichment = False # Disabling formulas to save VRAM
        options.generate_picture_images = True 
        options.images_scale = 0.8 # Lowering scale further for stability
        options.generate_page_images = False
        
        # Limit memory buffer queues during processing of huge PDFs
        if hasattr(options, 'queue_max_size'):
            options.queue_max_size = 5
        
        # Hardware acceleration
        device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
        options.accelerator_options = AcceleratorOptions(device=device)
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options)
            }
        )
        logger.info(f"Docling initialized using {device} (Memory Optimized Mode)")

    async def parse_pdf(self, pdf_path: Path, article_meta: Dict[str, Any], vlm_describer: Optional[ImageFilter] = None, publish_event = None, project_id: str = None) -> str:
        """
        Converts PDF to enriched Markdown.
        1. Docling conversion (Structural MD)
        2. VLM image descriptions (optional)
        3. Table flattening
        4. YAML Front-matter injection
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")

        # Determine total pages using pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
        except Exception as e:
            logger.warning(f"Could not read PDF pages via pypdf, falling back to full processing: {e}")
            total_pages = 9999
            
        import gc
        import torch
        import psutil

        chunk_size = 10 
        md_parts = []
        all_images = []
        loop = asyncio.get_running_loop()

        for start_page in range(1, total_pages + 1, chunk_size):
            end_page = min(start_page + chunk_size - 1, total_pages)
            if start_page > total_pages:
                break
                
            try:
                # 1. Run Docling for the current page chunk
                if total_pages != 9999:
                    if publish_event:
                        await publish_event(project_id, {
                            "type": "sub_progress", 
                            "msg": f"Analizando páginas {start_page}-{end_page} de {total_pages}..."
                        })
                    result = await loop.run_in_executor(
                        None, 
                        lambda: self.converter.convert(str(pdf_path), page_range=(start_page, end_page))
                    )
                else:
                    result = await loop.run_in_executor(None, self.converter.convert, str(pdf_path))
                    
                doc = result.document

                # 2. Extract Document Images for VLM later
                if hasattr(doc, "pictures"):
                    for element in doc.pictures:
                        try:
                            img = element.get_image(doc)
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG')
                            all_images.append(img_byte_arr.getvalue())
                        except Exception as e:
                            logger.error(f"Error extracting image from chunk {start_page}-{end_page}: {e}")

                # 3. Export this chunk to Markdown
                md_parts.append(doc.export_to_markdown())
            except Exception as loop_e:
                logger.error(f"Docling error on chunk {start_page}-{end_page}: {loop_e}")
            
            # Heavy GC and CUDA cache clear to free memory after heavy chunk
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Log periodic memory status
            process = psutil.Process()
            mem_info = process.memory_info().rss / (1024 * 1024)
            logger.info(f"Chunk {start_page}-{end_page} completed. Backend RAM: {mem_info:.2f} MB")

            if total_pages == 9999:
                break # Only one unchunked pass
                
        # Join chunks together
        md_content = "\n\n".join(md_parts)

        # 4. VLM Integration: Sequentially describe collected images
        image_map = {}
        if vlm_describer and all_images:
            total_imgs = len(all_images)
            for i, img_bytes in enumerate(all_images):
                if publish_event:
                    await publish_event(project_id, {
                        "type": "sub_progress", 
                        "msg": f"Describiendo imagen {i+1}/{total_imgs} con VLM..."
                    })
                try:
                    desc = await vlm_describer.analyze_image_bytes(img_bytes)
                    if desc:
                        image_map[i] = desc
                except Exception as e:
                    logger.error(f"Error describing image {i} with VLM: {e}")

        # 5. Inject VLM descriptions into MD sequentially
        if image_map:
            img_idx = 0
            def _inject_desc(match):
                nonlocal img_idx
                desc = image_map.get(img_idx)
                img_idx += 1
                if desc:
                    return f"\n\n> **[💡 Descripción de Imagen VLM]:** {desc}\n\n"
                # If no description or failed VLM, keep the tag for visibility or remove if preferred.
                return match.group(0)

            md_content = re.sub(r"<!--\s*image\s*-->", _inject_desc, md_content)

        # 5. Flatten Tables
        md_content = TableFlattener.flatten(md_content, article_meta)

        # 6. Prepend YAML Front-matter
        front_matter = {
            "agrisearch_id": article_meta.get("id"),
            "doi": article_meta.get("doi"),
            "title": article_meta.get("title"),
            "authors": article_meta.get("authors"),
            "year": article_meta.get("year"),
            "journal": article_meta.get("journal"),
            "keywords": article_meta.get("keywords") or [],
            "source_database": article_meta.get("source_database")
        }
        
        yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
        final_md = f"---\n{yaml_str}---\n\n{md_content}"

        return final_md
