"""
Archivo: test_scihub_service.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para el componente `SciHubDownloader`. Valida la 
integración con los mirrors de Sci-Hub mediante el uso de mocks para la librería 
base. Asegura que se respeten los límites de frecuencia de descarga (rate 
limiting), se gestionen correctamente las rutas de almacenamiento y se 
manejen casos donde el PDF no está disponible.

Acciones Principales:
    - Validación de recuperación exitosa de contenido binario (PDF).
    - Simulación de artículos no encontrados en Sci-Hub.
    - Verificación del guardado físico de archivos en directorios temporales.
    - Prueba de estrés para el mecanismo de bloqueo y espera (Rate Limiting).
    - Verificación de creación automática de directorios de descarga.

Estructura Interna:
    - `TestSciHubDownloader`: Clase contenedora de los casos de prueba de descarga.

Entradas / Dependencias:
    - `app.services.scihub_service`.
    - `pytest`, `unittest.mock`.

Salidas / Efectos:
    - Verifica el cumplimiento del Rate Limiting mediante mediciones de tiempo.
    - Crea y elimina directorios temporales para validar el sistema de archivos.

Ejecución:
    pytest tests/backend/unit/test_scihub_service.py
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from app.services.scihub_service import SciHubDownloader


class TestSciHubDownloader:
    """Tests de SciHubDownloader."""

    @pytest.mark.asyncio
    async def test_download_by_doi_success(self):
        """Mock de SciHub.fetch devuelve PDF."""
        downloader = SciHubDownloader(download_dir=Path("/tmp/test"), rate_limit=0.01)

        mock_sh = MagicMock()
        mock_sh.fetch.return_value = {"pdf": b"%PDF-1.4 fake content", "url": "http://example.com"}
        downloader.sh = mock_sh

        result = await downloader.download_by_doi("10.1234/test")
        assert result is not None
        assert result["pdf"] == b"%PDF-1.4 fake content"

    @pytest.mark.asyncio
    async def test_download_by_doi_not_found(self):
        """SciHub.fetch devuelve None cuando no encuentra."""
        downloader = SciHubDownloader(download_dir=Path("/tmp/test"), rate_limit=0.01)

        mock_sh = MagicMock()
        mock_sh.fetch.return_value = None
        downloader.sh = mock_sh

        result = await downloader.download_by_doi("10.9999/nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_download_and_save_creates_file(self):
        """download_and_save guarda el PDF en disco."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SciHubDownloader(download_dir=Path(tmpdir), rate_limit=0.01)

            mock_sh = MagicMock()
            mock_sh.fetch.return_value = {"pdf": b"%PDF-1.4 test content", "url": "http://example.com"}
            downloader.sh = mock_sh

            path = await downloader.download_and_save("10.1234/test", "art-001")
            assert path is not None
            assert Path(path).exists()
            assert Path(path).read_bytes() == b"%PDF-1.4 test content"

    @pytest.mark.asyncio
    async def test_download_and_save_returns_none_on_failure(self):
        """download_and_save retorna None si falla."""
        downloader = SciHubDownloader(download_dir=Path("/tmp/test"), rate_limit=0.01)

        mock_sh = MagicMock()
        mock_sh.fetch.return_value = None
        downloader.sh = mock_sh

        path = await downloader.download_and_save("10.9999/nonexistent", "art-002")
        assert path is None

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Dos requests en <rate_limit: el segundo espera."""
        downloader = SciHubDownloader(download_dir=Path("/tmp/test"), rate_limit=0.5)

        mock_sh = MagicMock()
        mock_sh.fetch.return_value = {"pdf": b"content", "url": "http://example.com"}
        downloader.sh = mock_sh

        start = time.time()
        await downloader.download_by_doi("10.1234/test1")
        await downloader.download_by_doi("10.1234/test2")
        elapsed = time.time() - start

        assert elapsed >= 0.4  # Should have waited ~0.5s

    def test_download_dir_created(self):
        """Download dir se crea al instanciar."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "subdir" / "deep"
            downloader = SciHubDownloader(download_dir=nested, rate_limit=0.01)
            assert nested.exists()
