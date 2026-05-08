"""
Archivo: scihub_service.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Servicio de descarga de PDFs científicos a través de Sci-Hub. Implementado como
mecanismo de último recurso para artículos que se encuentran bajo muros de pago
(paywalls) y no están disponibles en repositorios Open Access tradicionales.

ADVERTENCIA: Este servicio solo debe activarse por solicitud explícita del usuario
y cumple con políticas estrictas de rate limiting para evitar bloqueos.

Acciones Principales:
    - Búsqueda de artículos en Sci-Hub mediante DOI.
    - Control de flujo (Rate Limiting) para peticiones secuenciales.
    - Almacenamiento local persistente de los PDFs recuperados.

Estructura Interna:
    - `SciHubDownloader`: Clase encargada de la orquestación de descargas.

Entradas / Dependencias:
    - `scihub.py`: Librería base para interacción con los mirrors.
    - `asyncio`: Para la gestión de bloqueos.

Salidas / Efectos:
    - Descarga y guarda archivos `.pdf` en el directorio especificado.
    - Actualiza el estado de disponibilidad del artículo en el sistema.

Ejemplo de Integración:
    from app.services.scihub_service import SciHubDownloader
    downloader = SciHubDownloader(download_dir=Path("downloads/"))
    path = await downloader.download_and_save("10.1038/nature12345", "art_001")
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from scihub import SciHub

logger = logging.getLogger(__name__)


class SciHubDownloader:
    """
    Orquestador de descargas para Sci-Hub con soporte para rate limiting.
    """

    def __init__(self, download_dir: Path, rate_limit: float = 10.0):
        """
        Inicializa el descargador de Sci-Hub.

        Args:
            download_dir (Path): Directorio donde se guardarán los PDFs.
            rate_limit (float): Tiempo de espera obligatorio entre peticiones (segundos).
        """
        self.sh = SciHub()
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def download_by_doi(self, doi: str) -> Optional[dict]:
        """
        Descarga el PDF desde Sci-Hub usando un DOI.

        Este método utiliza un bloqueo (Lock) para garantizar que se respete el
        límite de peticiones por segundo definido en `rate_limit`.

        Args:
            doi (str): El DOI del artículo a buscar.

        Returns:
            Optional[dict]: Diccionario con los datos del artículo (incluyendo el PDF binario)
            o None si la descarga falló o el artículo no se encontró.
        """
        async with self._lock:
            elapsed = asyncio.get_event_loop().time() - self._last_request
            if elapsed < self.rate_limit:
                wait = self.rate_limit - elapsed
                logger.debug("Sci-Hub rate limit: esperando %.1fs", wait)
                await asyncio.sleep(wait)

            logger.info("Sci-Hub: buscando %s", doi)
            try:
                result = await asyncio.to_thread(self.sh.fetch, doi)
            except Exception as e:
                logger.warning("Sci-Hub: error para %s: %s", doi, e)
                self._last_request = asyncio.get_event_loop().time()
                return None

            self._last_request = asyncio.get_event_loop().time()

            if result and result.get("pdf"):
                size_kb = len(result["pdf"]) / 1024
                logger.info("Sci-Hub: descargado %s (%.0f KB)", doi, size_kb)
            else:
                logger.warning("Sci-Hub: no encontrado %s", doi)
            return result

    async def download_and_save(self, doi: str, article_id: str) -> Optional[str]:
        """
        Descarga el PDF y lo almacena localmente en el sistema de archivos.

        Args:
            doi (str): El DOI del artículo.
            article_id (str): El ID interno del artículo para nombrar el archivo.

        Returns:
            Optional[str]: La ruta local absoluta del archivo PDF guardado, 
            o None si no se pudo descargar/guardar.
        """
        result = await self.download_by_doi(doi)
        if not result or not result.get("pdf"):
            return None

        safe_doi = doi.replace("/", "_").replace("\\", "_")[:100]
        filename = f"scihub_{article_id}_{safe_doi}.pdf"
        filepath = self.download_dir / filename
        await asyncio.to_thread(filepath.write_bytes, result["pdf"])
        return str(filepath)
