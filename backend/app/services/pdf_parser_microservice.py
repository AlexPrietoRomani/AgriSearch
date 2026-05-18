"""
Microservicio de Parseo PDF — Capa de Abstracción de Proveedores.

Arquitectura:
┌─────────────────────────────────────────────────────────┐
│                    App Principal                         │
│              (pdf_enrichment_service.py)                 │
└────────────────────────┬────────────────────────────────┘
                         │ llama
┌────────────────────────▼────────────────────────────────┐
│              PDFParserMicroservice                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  PDFParserProvider (protocol/ABC)                 │  │
│  │  - parse(pdf_path, meta) -> str                   │  │
│  │  - get_engine_name() -> str                       │  │
│  │  - is_available() -> bool                         │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │OpenDataLoader│  │  MarkItDown  │  │   Futuro:    │  │
│  │  Provider    │  │  Provider    │  │  Grobid/etc  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Fallback Chain: OpenDataLoader → MarkItDown → Error    │
└─────────────────────────────────────────────────────────┘

Ventajas sobre run_in_executor:
- Timeout real con process.kill() para OpenDataLoader
- No deja procesos Java huérfanos
- Streams redirigidos a DEVNULL (sin pipe deadlocks en Windows)
- Memoria liberada instantáneamente al matar el proceso
- Cambio de proveedor futuro: solo implementar PDFParserProvider
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import asyncio
import logging
import tempfile

logger = logging.getLogger(__name__)


# ─── Excepciones específicas ─────────────────────────────────────────────

class ParserTimeoutError(TimeoutError):
    """Excepción específica para timeouts de parseo."""
    pass


class ParserError(Exception):
    """Excepción específica para errores de parseo."""
    pass


# ─── Interfaz abstracta ──────────────────────────────────────────────────

class PDFParserProvider(ABC):
    """
    Contrato abstracto para proveedores de parseo PDF.
    
    Cualquier motor de conversión PDF→Markdown debe implementar
    esta interfaz para ser compatible con el microservicio.
    """
    
    @abstractmethod
    async def parse(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> str:
        """
        Convierte un PDF a Markdown enriquecido.
        
        Args:
            pdf_path: Ruta absoluta al PDF.
            article_meta: Metadatos del artículo (doi, title, authors, etc.).
            publish_event: Función async para eventos SSE (opcional).
            project_id: ID del proyecto para eventos SSE (opcional).
        
        Returns:
            String con Markdown enriquecido (front-matter YAML + contenido).
        
        Raises:
            ParserTimeoutError: Si excede el timeout del proveedor.
            ParserError: Si falla la conversión.
        """
        ...
    
    @abstractmethod
    def get_engine_name(self) -> str:
        """Retorna el nombre identificador del motor (ej: 'opendataloader', 'markitdown')."""
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el motor está disponible (dependencias instaladas, Java, etc.)."""
        ...


# ─── Proveedor: OpenDataLoader (subproceso asíncrono) ─────────────────────

class OpenDataLoaderSubprocessProvider(PDFParserProvider):
    """
    Proveedor de OpenDataLoader ejecutado como subproceso asíncrono controlable.
    
    Reemplaza run_in_executor() por asyncio.create_subprocess_exec para:
    - Timeout real con process.kill()
    - No dejar procesos Java huérfanos
    - Streams redirigidos a DEVNULL (sin pipe deadlocks en Windows)
    - Memoria liberada instantáneamente al matar el proceso
    """
    
    DEFAULT_TIMEOUT = 90.0  # segundos
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._jar_path: Optional[str] = None
        self._locate_jar()
    
    def _locate_jar(self) -> None:
        """Localiza el JAR embebido de opendataloader-pdf."""
        try:
            import importlib.resources as resources
            self._jar_path = str(
                resources.files("opendataloader_pdf").joinpath("jar", "opendataloader-pdf-cli.jar")
            )
        except Exception:
            try:
                import opendataloader_pdf
                self._jar_path = str(
                    Path(opendataloader_pdf.__file__).parent / "jar" / "opendataloader-pdf-cli.jar"
                )
            except ImportError:
                self._jar_path = None
    
    def get_engine_name(self) -> str:
        return "opendataloader"
    
    def is_available(self) -> bool:
        return self._jar_path is not None and Path(self._jar_path).exists()
    
    async def parse(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> str:
        if not self.is_available():
            raise ParserError("OpenDataLoader JAR no encontrado")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": f"Convirtiendo PDF con OpenDataLoader (timeout: {self.timeout}s)..."
            })
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = [
                "java", "-jar", self._jar_path,
                str(pdf_path),
                "--output-dir", tmp_dir,
                "--format", "markdown",
                "--table-method", "cluster",
                "--reading-order", "xycut",
            ]
            
            # Subproceso asíncrono con streams a DEVNULL
            # Esto previene deadlocks en pipes de Windows y permite matar el proceso limpiamente
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            
            logger.debug(f"OpenDataLoader PID: {process.pid} para {pdf_path.name}")
            
            try:
                # Esperar con un límite estricto para evitar bucles infinitos en Java
                await asyncio.wait_for(process.wait(), timeout=self.timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout ({self.timeout}s) en OpenDataLoader para {pdf_path.name}. "
                    f"Matando proceso {process.pid}..."
                )
                try:
                    process.kill()
                    await process.wait()
                except Exception as kill_err:
                    logger.error(f"No se pudo matar el proceso java {process.pid}: {kill_err}")
                raise ParserTimeoutError(
                    f"OpenDataLoader excedió {self.timeout}s para {pdf_path.name}"
                )
            
            # Leer resultado
            md_files = list(Path(tmp_dir).glob("*.md"))
            if not md_files:
                raise ParserError(f"OpenDataLoader no generó .md para {pdf_path.name}")
            
            md_content = md_files[0].read_text(encoding="utf-8")
            
            if len(md_content.strip()) < 50:
                logger.warning(f"Contenido muy corto de OpenDataLoader: {len(md_content)} chars")
            
            return md_content


# ─── Proveedor: MarkItDown (CPU puro) ─────────────────────────────────────

class MarkItDownProvider(PDFParserProvider):
    """
    Proveedor de MarkItDown como motor de parseo PDF (y multi-formato).
    
    Ventajas:
    - CPU puro (~50MB RAM), sin Java
    - Soporta PDF, DOCX, PPTX, XLSX, HTML, EPUB, CSV
    - No entra en bucles infinitos con fuentes corruptas
    - Timeout natural (no necesita kill externo)
    """
    
    DEFAULT_TIMEOUT = 300.0  # 5 minutos (más generoso, es más lento pero seguro)
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, llm_client=None, llm_model: str = None):
        self.timeout = timeout
        self.llm_client = llm_client
        self.llm_model = llm_model
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        try:
            from markitdown import MarkItDown
            return True
        except ImportError:
            return False
    
    def get_engine_name(self) -> str:
        return "markitdown"
    
    def is_available(self) -> bool:
        return self._available
    
    async def parse(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> str:
        if not self.is_available():
            raise ParserError("MarkItDown no está instalado")
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {pdf_path}")
        
        if publish_event and project_id:
            await publish_event(project_id, {
                "type": "sub_progress",
                "msg": f"Convirtiendo PDF con MarkItDown (CPU)..."
            })
        
        from markitdown import MarkItDown
        
        md = MarkItDown(llm_client=self.llm_client, llm_model=self.llm_model)
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: md.convert(str(pdf_path))
        )
        
        md_content = result.text_content
        
        if len(md_content.strip()) < 50:
            logger.warning(f"Contenido muy corto de MarkItDown: {len(md_content)} chars")
        
        return md_content


# ─── Orquestador: Microservicio con fallback chain ────────────────────────

class PDFParserMicroservice:
    """
    Microservicio de parseo PDF con cadena de fallback automática.
    
    Flujo:
    1. Intenta OpenDataLoader (subproceso asíncrono, timeout 90s).
    2. Si timeout/falla → MarkItDown (timeout 300s).
    3. Si ambos fallan → ParserError con detalles.
    
    Diseño para cambio de proveedor futuro:
    - Añadir nuevo proveedor: implementar PDFParserProvider.
    - Cambiar orden de fallback: modificar self._providers en __init__.
    - Cambiar timeout: ajustar parámetros del proveedor.
    
    Ejemplo:
        ms = PDFParserMicroservice(opendataloader_timeout=90.0)
        md_content, engine = await ms.parse(pdf_path, meta)
    """
    
    def __init__(
        self,
        opendataloader_timeout: float = 90.0,
        markitdown_timeout: float = 300.0,
        llm_client=None,
        llm_model: str = None,
    ):
        self._providers: list[PDFParserProvider] = []
        
        # Registrar proveedores en orden de prioridad
        odl = OpenDataLoaderSubprocessProvider(timeout=opendataloader_timeout)
        if odl.is_available():
            self._providers.append(odl)
            logger.info("Proveedor OpenDataLoader registrado (subproceso asíncrono)")
        
        mit = MarkItDownProvider(
            timeout=markitdown_timeout,
            llm_client=llm_client,
            llm_model=llm_model,
        )
        if mit.is_available():
            self._providers.append(mit)
            logger.info("Proveedor MarkItDown registrado (CPU)")
        
        if not self._providers:
            logger.error("No hay proveedores de parseo disponibles")
    
    async def parse(
        self,
        pdf_path: Path,
        article_meta: Dict[str, Any],
        publish_event=None,
        project_id: str = None,
    ) -> tuple[str, str]:
        """
        Ejecuta la cadena de fallback y retorna (markdown, engine_used).
        
        Args:
            pdf_path: Ruta al PDF.
            article_meta: Metadatos del artículo.
            publish_event: Función async para eventos SSE.
            project_id: ID del proyecto.
        
        Returns:
            Tupla (markdown_content, engine_name).
        
        Raises:
            ParserError: Si todos los proveedores fallan.
        """
        last_error: Optional[Exception] = None
        
        for provider in self._providers:
            engine = provider.get_engine_name()
            try:
                logger.info(f"Intentando parseo con {engine}...")
                md_content = await provider.parse(
                    pdf_path, article_meta, publish_event, project_id
                )
                logger.info(f"Parseo exitoso con {engine} ({len(md_content)} chars)")
                return md_content, engine
            except (ParserTimeoutError, ParserError, Exception) as e:
                last_error = e
                logger.warning(f"Proveedor {engine} falló: {e}")
                
                # Notificar fallback via SSE
                if publish_event and project_id:
                    await publish_event(project_id, {
                        "type": "sub_progress",
                        "msg": f"{engine} falló. Usando siguiente proveedor..."
                    })
        
        # Todos los proveedores fallaron
        error_msg = f"Todos los proveedores fallaron para {pdf_path.name}: {last_error}"
        logger.error(error_msg)
        raise ParserError(error_msg)
    
    def get_available_engines(self) -> list[str]:
        """Lista de motores disponibles en orden de prioridad."""
        return [p.get_engine_name() for p in self._providers]
