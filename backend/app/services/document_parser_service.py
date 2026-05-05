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
import tempfile
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

# ─── OpenDataLoader PDF (Java + CPU, #1 en benchmarks) ──────────────────
try:
    import opendataloader_pdf
    OPENDATALOADER_AVAILABLE = True
except ImportError:
    opendataloader_pdf = None
    OPENDATALOADER_AVAILABLE = False

logger = logging.getLogger(__name__)

class TableFlattener:
    """
    Transforms Markdown tables into natural language sentences.
    Each row becomes a sentence referencing its headers to preserve context.
    """
    # Regex to detect Markdown table blocks
    _TABLE_PATTERN = re.compile(
        r"((?:^\|[^\n]+\|\s*$\n?){2,})",
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


import warnings

class ImageFilter:
    """
    @deprecated
    Filters decorative images and describes technical ones using a VLM.
    (This class is deprecated. VLM processing is now handled natively by MarkItDownParser).
    """
    SYSTEM_PROMPT = (
        "Eres un analista experto en extracción de datos científicos. "
        "Describe en un único párrafo corto y directo qué representa esta imagen "
        "(ej: 'Gráfico de barras mostrando la relación entre X e Y'). "
        "Si la imagen es un logo, publicidad, decorativa o ilegible, "
        "responde ÚNICAMENTE con la palabra: DESCARTAR."
    )

    def __init__(self, model_name: str = "llama3.2-vision"):
        warnings.warn(
            "ImageFilter is deprecated and will be removed. "
            "Use MarkItDownParser with an llm_client instead.",
            DeprecationWarning,
            stacklevel=2
        )
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
    DEPRECATED: Reemplazado por OpenDataLoaderParser + MarkItDownParser.
    Se mantiene como referencia hasta confirmar estabilidad del nuevo pipeline.
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
        options.do_ocr = True  # Enable OCR for scanned PDFs
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
            "source_database": article_meta.get("source_database"),
            "parser_engine": "docling",
        }
        
        yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
        final_md = f"---\n{yaml_str}---\n\n{md_content}"

        return final_md

# ─── MarkItDown Parser (CPU-based, Zero-GPU) ─────────────────────────────
try:
    from markitdown import MarkItDown as _MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    _MarkItDown = None
    MARKITDOWN_AVAILABLE = False


class OllamaVLMWrapper:
    """
    Puente adaptador para conectar MarkItDown con modelos multimodales locales en Ollama.
    Garantiza que el payload de imagen y el prompt sean 100% compatibles con gemma4:26b.
    """
    class Completions:
        def __init__(self, parent_wrapper):
            self.parent_wrapper = parent_wrapper
            self.base_url = parent_wrapper.base_url

        def create(self, **kwargs):
            """Redirige la petición a la API nativa de Ollama para mayor robustez."""
            import requests
            import json
            import base64

            # Utilizar el modelo de kwargs, o el por defecto configurado
            model = kwargs.get("model", self.parent_wrapper.default_model)
            messages = kwargs.get("messages", [])
            temperature = kwargs.get("temperature", 0.0)
            
            # Formatear mensajes para la API nativa de Ollama
            ollama_messages = []
            ollama_images = []

            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                
                text_content = ""
                if isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text":
                            text_content += part.get("text", "")
                        elif part.get("type") == "image_url":
                            url = part.get("image_url", {}).get("url", "")
                            # Extraer base64 puro (sin prefijo)
                            if url.startswith("data:image"):
                                if "," in url:
                                    ollama_images.append(url.split(",")[1])
                                else:
                                    ollama_images.append(url)
                            else:
                                ollama_images.append(url)
                else:
                    text_content = str(content)

                msg_obj = {"role": role, "content": text_content}
                if ollama_images and role == "user":
                    msg_obj["images"] = ollama_images
                
                ollama_messages.append(msg_obj)

            # Preparar payload nativo
            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            logger.info(f"Enviando petición VLM NATIVA a Ollama: {model} ({len(ollama_images)} imágenes)")
            
            base_url = self.parent_wrapper.base_url
            endpoint = base_url.replace("/v1", "/api/chat") if "/v1" in base_url else f"{base_url}/api/chat"
            
            try:
                response = requests.post(endpoint, json=payload, timeout=180)
                response.raise_for_status()
                data = response.json()
                
                # Mockear la respuesta al formato de OpenAI que espera MarkItDown
                class MockMessage:
                    def __init__(self, content):
                        self.content = content
                
                class MockChoice:
                    def __init__(self, content):
                        self.message = MockMessage(content)
                
                class MockResponse:
                    def __init__(self, content):
                        self.choices = [MockChoice(content)]
                
                return MockResponse(data.get("message", {}).get("content", ""))
                
            except Exception as e:
                logger.error(f"Error en el puente NATIVO Ollama: {e}")
                raise

    class Chat:
        def __init__(self, parent_wrapper):
            self.completions = parent_wrapper.Completions(parent_wrapper)

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "gemma4:26b"):
        self.base_url = base_url
        self.default_model = default_model
        self.chat = self.Chat(self)


class MarkItDownParser:
    """
    Convierte PDFs a Markdown estructurado usando Microsoft MarkItDown.
    Opera completamente en CPU — sin dependencia de GPU ni modelos pesados.
    
    Atributos:
        md: Instancia de MarkItDown configurada.
        has_vlm: Indica si hay un VLM disponible para describir imágenes.
    """

    def __init__(self, llm_client=None, llm_model: str = None):
        """
        Inicializa el parser.
        
        Args:
            llm_client: Cliente OpenAI-compatible (openai.OpenAI o OllamaVLMWrapper).
                        Opcional. Si se proporciona, MarkItDown describirá imágenes automáticamente.
            llm_model:  Nombre del modelo VLM (ej: "gemma4:26b", "llama3.2-vision").
        """
        if not MARKITDOWN_AVAILABLE:
            raise ImportError(
                "MarkItDown no está instalado. Ejecuta: uv add 'markitdown[pdf]'"
            )
        
        init_kwargs = {}
        self.has_vlm = False
        
        if llm_client and llm_model:
            # Si se pasa una URL de Ollama pero no el cliente wrapper, lo creamos automáticamente
            if isinstance(llm_client, str) and "http" in llm_client:
                logger.info(f"Detectada URL de Ollama. Inicializando OllamaVLMWrapper para {llm_model}...")
                llm_client = OllamaVLMWrapper(base_url=llm_client, default_model=llm_model)

            init_kwargs["llm_client"] = llm_client
            init_kwargs["llm_model"] = llm_model
            init_kwargs["llm_prompt"] = (
                "Eres un analista experto en extracción de datos científicos. "
                "Describe esta imagen de un artículo de investigación en JSON o texto plano: "
                "1. Tipo de figura (gráfico, tabla, foto, diagrama). "
                "2. Variables principales. "
                "3. Hallazgo clave. "
                "Sé directo y conciso en español. "
                "Si la imagen es irrelevante, responde solo DESCARTAR."
            )
            # Habilitar plugins (necesario para markitdown-ocr si está instalado)
            init_kwargs["enable_plugins"] = True
            self.has_vlm = True
            logger.info(f"MarkItDown inicializado con VLM: {llm_model} vía Puente Adaptativo")
        
        self.md = _MarkItDown(**init_kwargs)
        logger.info(
            f"MarkItDown inicializado (CPU) | VLM: {'activo' if self.has_vlm else 'inactivo'}"
        )

    async def parse_pdf(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> str:
        """
        Convierte un PDF a Markdown enriquecido.
        
        Pipeline:
          1. MarkItDown convierte el PDF completo a Markdown (CPU).
          2. TableFlattener aplana tablas en oraciones atómicas para RAG.
          3. Se inyecta front-matter YAML con metadatos bibliográficos.
        
        Args:
            pdf_path:      Ruta absoluta al archivo PDF.
            article_meta:  Dict con claves: id, doi, title, authors, year,
                          journal, keywords, source_database.
            publish_event: Función async para enviar progreso via SSE (opcional).
            project_id:    ID del proyecto para los eventos SSE (opcional).
        
        Returns:
            String con el Markdown enriquecido completo (YAML + contenido + tablas aplanadas).
        
        Raises:
            FileNotFoundError: Si el PDF no existe en la ruta indicada.
        """
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        # ── 1. Conversión PDF → Markdown (CPU) ──────────────────────
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": f"Convirtiendo PDF a Markdown (MarkItDown CPU)..."
            })

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: self.md.convert(str(pdf_path))
        )
        md_content = result.markdown

        if not md_content or len(md_content.strip()) < 50:
            logger.warning(f"Conversión vacía o muy corta para {pdf_path.name}")
            md_content = f"<!-- MarkItDown: conversión vacía para {pdf_path.name} -->"

        # ── 2. Limpiar artefactos de conversión ──────────────────────
        md_content = self._post_process(md_content)

        # ── 3. Filtrar descripciones VLM de imágenes decorativas ─────
        if self.has_vlm:
            md_content = self._filter_discarded_images(md_content)

        # ── 4. Aplanar tablas para RAG ───────────────────────────────
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": "Aplanando tablas para optimización RAG..."
            })
        md_content = TableFlattener.flatten(md_content, article_meta)

        # ── 5. Inyectar front-matter YAML ────────────────────────────
        front_matter = {
            "agrisearch_id": article_meta.get("id"),
            "doi": article_meta.get("doi"),
            "title": article_meta.get("title"),
            "authors": article_meta.get("authors"),
            "year": article_meta.get("year"),
            "journal": article_meta.get("journal"),
            "keywords": article_meta.get("keywords") or [],
            "source_database": article_meta.get("source_database"),
            "parser_engine": "markitdown",
        }
        yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
        final_md = f"---\n{yaml_str}---\n\n{md_content}"

        return final_md

    @staticmethod
    def _post_process(md_text: str) -> str:
        """Limpia artefactos comunes de la conversión PDF→MD."""
        # Eliminar líneas vacías excesivas (más de 2 consecutivas)
        md_text = re.sub(r"\n{4,}", "\n\n\n", md_text)
        # Eliminar headers vacíos (## \n)
        md_text = re.sub(r"^(#{1,6})\s*$", "", md_text, flags=re.MULTILINE)
        # Normalizar separadores de página
        md_text = re.sub(r"-{5,}", "---", md_text)
        return md_text.strip()

    @staticmethod
    def _filter_discarded_images(md_text: str) -> str:
        """Elimina bloques de imagen cuya descripción VLM dice DESCARTAR."""
        # Patrón: líneas que contengan DESCARTAR en contexto de descripción de imagen
        md_text = re.sub(
            r"!\[.*?\]\(.*?\)\s*\n*.*?DESCARTAR.*?\n*",
            "",
            md_text,
            flags=re.IGNORECASE,
        )
        return md_text


# ─── OpenDataLoader PDF Parser (Java + CPU, #1 en benchmarks) ────────────


class OpenDataLoaderParser:
    """
    Convierte PDFs de artículos científicos a Markdown usando OpenDataLoader PDF.
    
    Motor #1 en benchmarks (0.907 overall, 0.928 en tablas).
    Opera en CPU (Java JVM) — sin dependencia de GPU.
    Detecta layout de doble columna, tablas borderless, y fórmulas LaTeX.
    
    Requiere: Java 11+ instalado en el sistema.
    """

    def __init__(self, hybrid_mode: bool = False, hybrid_port: int = 5002):
        """
        Inicializa el parser.
        
        Args:
            hybrid_mode: Si True, usa el servidor hybrid para OCR/fórmulas/imágenes.
                         Requiere `opendataloader-pdf-hybrid` corriendo en hybrid_port.
            hybrid_port: Puerto del servidor hybrid (default: 5002).
        """
        if not OPENDATALOADER_AVAILABLE:
            raise ImportError(
                "OpenDataLoader PDF no está instalado. "
                "Ejecuta: uv add opendataloader-pdf\n"
                "También requiere Java 11+: java -version"
            )
        
        self.hybrid_mode = hybrid_mode
        self.hybrid_port = hybrid_port
        logger.info(
            f"OpenDataLoaderParser inicializado (Java+CPU) | "
            f"Híbrido: {'activo' if hybrid_mode else 'inactivo'}"
        )

    async def parse_pdf(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> str:
        """
        Convierte un PDF científico a Markdown estructurado.
        
        Pipeline:
          1. OpenDataLoader convierte el PDF (Java JVM, CPU).
          2. TableFlattener aplana tablas en oraciones atómicas para RAG.
          3. Se inyecta front-matter YAML con metadatos bibliográficos.
        
        Args:
            pdf_path:      Ruta absoluta al archivo PDF.
            article_meta:  Dict con claves: id, doi, title, authors, year,
                          journal, keywords, source_database.
            publish_event: Función async para enviar progreso via SSE (opcional).
            project_id:    ID del proyecto para los eventos SSE (opcional).
        
        Returns:
            String con el Markdown enriquecido completo (YAML + contenido + tablas aplanadas).
        """
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        # ── 1. Conversión PDF → Markdown (Java JVM, CPU) ─────────────
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": f"Convirtiendo PDF con OpenDataLoader (layout + tablas)..."
            })

        loop = asyncio.get_running_loop()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Ejecutar en thread pool (Java JVM es bloqueante)
            convert_kwargs = {
                "input_path": str(pdf_path),
                "output_dir": tmp_dir,
                "format": "markdown",
                "use_struct_tree": True,
                "table_method": "cluster",
                "reading_order": "xycut",
            }
            
            if self.hybrid_mode:
                convert_kwargs["hybrid"] = "docling-fast"
                convert_kwargs["hybrid_mode"] = "auto"
            
            await loop.run_in_executor(
                None, lambda: opendataloader_pdf.convert(**convert_kwargs)
            )
            
            # Leer el .md generado
            md_files = list(Path(tmp_dir).glob("*.md"))
            if not md_files:
                logger.warning(f"OpenDataLoader no generó .md para {pdf_path.name}")
                md_content = f"<!-- OpenDataLoader: conversión vacía para {pdf_path.name} -->"
            else:
                md_content = md_files[0].read_text(encoding="utf-8")

        if len(md_content.strip()) < 50:
            logger.warning(f"Contenido muy corto para {pdf_path.name}: {len(md_content)} chars")

        # ── 2. Limpiar artefactos de conversión ──────────────────────
        md_content = self._post_process(md_content)

        # ── 3. Aplanar tablas para RAG ───────────────────────────────
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": "Aplanando tablas para optimización RAG..."
            })
        md_content = TableFlattener.flatten(md_content, article_meta)

        # ── 4. Inyectar front-matter YAML ────────────────────────────
        front_matter = {
            "agrisearch_id": article_meta.get("id"),
            "doi": article_meta.get("doi"),
            "title": article_meta.get("title"),
            "authors": article_meta.get("authors"),
            "year": article_meta.get("year"),
            "journal": article_meta.get("journal"),
            "keywords": article_meta.get("keywords") or [],
            "source_database": article_meta.get("source_database"),
            "parser_engine": "opendataloader",
        }
        yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
        final_md = f"---\n{yaml_str}---\n\n{md_content}"

        return final_md

    @staticmethod
    def _post_process(md_text: str) -> str:
        """Limpia artefactos comunes de la conversión PDF→MD."""
        md_text = re.sub(r"\n{4,}", "\n\n\n", md_text)
        md_text = re.sub(r"^(#{1,6})\s*$", "", md_text, flags=re.MULTILINE)
        md_text = re.sub(r"-{5,}", "---", md_text)
        return md_text.strip()
