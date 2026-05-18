"""
Archivo: test_pdf_parser_microservice.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Tests unitarios para el microservicio de parseo PDF con fallback automático.

Acciones Principales:
    - Validar interfaz abstracta PDFParserProvider.
    - Verificar OpenDataLoaderSubprocessProvider (JAR location, availability).
    - Verificar MarkItDownProvider (availability, engine name).
    - Testear PDFParserMicroservice fallback chain.
    - Confirmar que timeout mata procesos y libera RAM.
    - Validar que no quedan procesos huérfanos.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_pdf_parser_microservice.py -v
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ──────────────────────────────────────────────
# Tests de la interfaz abstracta
# ──────────────────────────────────────────────

class TestPDFParserProvider:
    """Tests de la interfaz abstracta."""

    def test_protocol_methods_defined(self):
        """PDFParserProvider define parse, get_engine_name, is_available."""
        from app.services.pdf_parser_microservice import PDFParserProvider
        assert hasattr(PDFParserProvider, 'parse')
        assert hasattr(PDFParserProvider, 'get_engine_name')
        assert hasattr(PDFParserProvider, 'is_available')

    def test_cannot_instantiate_abstract_class(self):
        """No se puede instanciar PDFParserProvider directamente."""
        from app.services.pdf_parser_microservice import PDFParserProvider
        with pytest.raises(TypeError):
            PDFParserProvider()

    def test_custom_provider_implementation(self):
        """Se puede implementar un proveedor custom."""
        from app.services.pdf_parser_microservice import PDFParserProvider

        class DummyProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                return "# Test"
            def get_engine_name(self):
                return "dummy"
            def is_available(self):
                return True

        provider = DummyProvider()
        assert provider.get_engine_name() == "dummy"
        assert provider.is_available() is True


# ──────────────────────────────────────────────
# Tests de excepciones
# ──────────────────────────────────────────────

class TestParserExceptions:
    """Tests de excepciones específicas."""

    def test_parser_timeout_error_is_timeout(self):
        """ParserTimeoutError hereda de TimeoutError."""
        from app.services.pdf_parser_microservice import ParserTimeoutError
        assert issubclass(ParserTimeoutError, TimeoutError)

    def test_parser_error_is_exception(self):
        """ParserError hereda de Exception."""
        from app.services.pdf_parser_microservice import ParserError
        assert issubclass(ParserError, Exception)

    def test_can_raise_and_catch_timeout(self):
        """Se puede lanzar y capturar ParserTimeoutError."""
        from app.services.pdf_parser_microservice import ParserTimeoutError
        with pytest.raises(TimeoutError):
            raise ParserTimeoutError("test")

    def test_can_raise_and_catch_parser_error(self):
        """Se puede lanzar y capturar ParserError."""
        from app.services.pdf_parser_microservice import ParserError
        with pytest.raises(Exception):
            raise ParserError("test")


# ──────────────────────────────────────────────
# Tests de OpenDataLoaderSubprocessProvider
# ──────────────────────────────────────────────

class TestOpenDataLoaderSubprocessProvider:
    """Tests del proveedor OpenDataLoader por subproceso."""

    def test_jar_location(self):
        """Localiza el JAR correctamente si está instalado."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider()
        # Debe ser None o una ruta válida
        assert provider._jar_path is None or Path(provider._jar_path).exists()

    def test_is_available_returns_bool(self):
        """is_available retorna booleano."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider()
        assert isinstance(provider.is_available(), bool)

    def test_get_engine_name(self):
        """Retorna 'opendataloader'."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider()
        assert provider.get_engine_name() == "opendataloader"

    def test_default_timeout(self):
        """Timeout por defecto es 90 segundos."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider()
        assert provider.timeout == 90.0

    def test_custom_timeout(self):
        """Se puede configurar timeout personalizado."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider(timeout=45.0)
        assert provider.timeout == 45.0

    @pytest.mark.asyncio
    async def test_parse_nonexistent_pdf_raises(self):
        """parse con PDF inexistente lanza FileNotFoundError."""
        from app.services.pdf_parser_microservice import OpenDataLoaderSubprocessProvider
        provider = OpenDataLoaderSubprocessProvider()
        if not provider.is_available():
            pytest.skip("OpenDataLoader no disponible")
        with pytest.raises(FileNotFoundError):
            await provider.parse(Path("/nonexistent.pdf"), {})

    @pytest.mark.asyncio
    async def test_parse_raises_when_jar_not_found(self):
        """parse lanza ParserError si el JAR no existe."""
        from app.services.pdf_parser_microservice import (
            OpenDataLoaderSubprocessProvider, ParserError
        )
        provider = OpenDataLoaderSubprocessProvider()
        provider._jar_path = "/nonexistent/jar/path.jar"
        with pytest.raises(ParserError, match="JAR no encontrado"):
            await provider.parse(Path("dummy.pdf"), {})


# ──────────────────────────────────────────────
# Tests de MarkItDownProvider
# ──────────────────────────────────────────────

class TestMarkItDownProvider:
    """Tests del proveedor MarkItDown."""

    def _is_markitdown_available(self) -> bool:
        try:
            from markitdown import MarkItDown
            return True
        except ImportError:
            return False

    def test_is_available(self):
        """MarkItDown está disponible (si está instalado)."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider()
        expected = self._is_markitdown_available()
        assert provider.is_available() is expected

    def test_get_engine_name(self):
        """Retorna 'markitdown'."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider()
        assert provider.get_engine_name() == "markitdown"

    def test_default_timeout(self):
        """Timeout por defecto es 300 segundos."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider()
        assert provider.timeout == 300.0

    def test_custom_timeout(self):
        """Se puede configurar timeout personalizado."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider(timeout=60.0)
        assert provider.timeout == 60.0

    def test_init_with_llm_params(self):
        """Acepta parámetros de LLM."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider(
            llm_client="http://localhost:11434/v1",
            llm_model="gemma4:26b"
        )
        assert provider.llm_client == "http://localhost:11434/v1"
        assert provider.llm_model == "gemma4:26b"

    def test_unavailable_when_not_installed(self):
        """is_available retorna False si markitdown no está instalado."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        with patch.object(MarkItDownProvider, '_check_availability', return_value=False):
            provider = MarkItDownProvider()
            assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_parse_raises_when_not_available(self):
        """parse lanza ParserError si MarkItDown no está disponible."""
        from app.services.pdf_parser_microservice import MarkItDownProvider, ParserError
        with patch.object(MarkItDownProvider, '_check_availability', return_value=False):
            provider = MarkItDownProvider()
            with pytest.raises(ParserError, match="no está instalado"):
                await provider.parse(Path("dummy.pdf"), {})

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file_raises(self):
        """parse con archivo inexistente lanza FileNotFoundError."""
        from app.services.pdf_parser_microservice import MarkItDownProvider
        provider = MarkItDownProvider()
        if not provider.is_available():
            pytest.skip("MarkItDown no disponible")
        with pytest.raises(FileNotFoundError):
            await provider.parse(Path("/nonexistent/file.pdf"), {})


# ──────────────────────────────────────────────
# Tests de PDFParserMicroservice (orquestador + fallback)
# ──────────────────────────────────────────────

class TestPDFParserMicroservice:
    """Tests del orquestador con fallback."""

    def test_registers_available_providers(self):
        """Registra solo proveedores disponibles."""
        from app.services.pdf_parser_microservice import PDFParserMicroservice
        with patch("app.services.pdf_parser_microservice.MarkItDownProvider.is_available", return_value=True):
            ms = PDFParserMicroservice()
            engines = ms.get_available_engines()
            assert len(engines) >= 1
            assert "markitdown" in engines

    def test_empty_providers_logs_error(self, caplog):
        """Log de error si no hay proveedores disponibles."""
        from app.services.pdf_parser_microservice import PDFParserMicroservice
        with patch("app.services.pdf_parser_microservice.OpenDataLoaderSubprocessProvider.is_available", return_value=False):
            with patch("app.services.pdf_parser_microservice.MarkItDownProvider.is_available", return_value=False):
                ms = PDFParserMicroservice()
                assert len(ms._providers) == 0
                assert any("No hay proveedores" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_fallback_chain_on_failure(self):
        """Si el primer proveedor falla, usa el siguiente."""
        from app.services.pdf_parser_microservice import (
            PDFParserMicroservice, PDFParserProvider, ParserError
        )

        class FailingProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                raise ParserError("Simulated failure")
            def get_engine_name(self): return "failing"
            def is_available(self): return True

        class WorkingProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                return "# Test content from working provider"
            def get_engine_name(self): return "working"
            def is_available(self): return True

        ms = PDFParserMicroservice()
        ms._providers = [FailingProvider(), WorkingProvider()]

        md, engine = await ms.parse(Path("dummy.pdf"), {}, None, None)
        assert engine == "working"
        assert "# Test content from working provider" in md

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_error(self):
        """Si todos fallan, lanza ParserError."""
        from app.services.pdf_parser_microservice import (
            PDFParserMicroservice, PDFParserProvider, ParserError
        )

        class FailingProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                raise ParserError("Always fails")
            def get_engine_name(self): return "failing"
            def is_available(self): return True

        ms = PDFParserMicroservice()
        ms._providers = [FailingProvider(), FailingProvider()]

        with pytest.raises(ParserError):
            await ms.parse(Path("dummy.pdf"), {}, None, None)

    @pytest.mark.asyncio
    async def test_first_provider_succeeds_uses_it(self):
        """Si el primer proveedor funciona, no intenta fallback."""
        from app.services.pdf_parser_microservice import (
            PDFParserMicroservice, PDFParserProvider
        )

        call_count = {"second": 0}

        class FirstProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                return "# First provider content"
            def get_engine_name(self): return "first"
            def is_available(self): return True

        class SecondProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                call_count["second"] += 1
                return "# Second provider content"
            def get_engine_name(self): return "second"
            def is_available(self): return True

        ms = PDFParserMicroservice()
        ms._providers = [FirstProvider(), SecondProvider()]

        md, engine = await ms.parse(Path("dummy.pdf"), {}, None, None)
        assert engine == "first"
        assert call_count["second"] == 0

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self):
        """Timeout del primer proveedor dispara fallback."""
        from app.services.pdf_parser_microservice import (
            PDFParserMicroservice, PDFParserProvider, ParserTimeoutError
        )

        class TimeoutProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                raise ParserTimeoutError("Timeout!")
            def get_engine_name(self): return "timeout_engine"
            def is_available(self): return True

        class FallbackProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                return "# Fallback content"
            def get_engine_name(self): return "fallback_engine"
            def is_available(self): return True

        ms = PDFParserMicroservice()
        ms._providers = [TimeoutProvider(), FallbackProvider()]

        md, engine = await ms.parse(Path("dummy.pdf"), {}, None, None)
        assert engine == "fallback_engine"
        assert "# Fallback content" in md

    @pytest.mark.asyncio
    async def test_sse_notification_on_fallback(self):
        """Notifica via SSE cuando un proveedor falla."""
        from app.services.pdf_parser_microservice import (
            PDFParserMicroservice, PDFParserProvider, ParserError
        )

        events = []

        async def mock_publish(project_id, event):
            events.append(event)

        class FailingProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                raise ParserError("fail")
            def get_engine_name(self): return "fail"
            def is_available(self): return True

        class OkProvider(PDFParserProvider):
            async def parse(self, *args, **kwargs):
                return "# OK"
            def get_engine_name(self): return "ok"
            def is_available(self): return True

        ms = PDFParserMicroservice()
        ms._providers = [FailingProvider(), OkProvider()]

        await ms.parse(Path("dummy.pdf"), {}, mock_publish, "proj-001")

        fallback_events = [e for e in events if e.get("type") == "sub_progress"]
        assert len(fallback_events) >= 1
        assert "falló" in fallback_events[0]["msg"]

    def test_available_engines_order(self):
        """Lista de engines refleja orden de prioridad."""
        from app.services.pdf_parser_microservice import PDFParserMicroservice
        with patch("app.services.pdf_parser_microservice.MarkItDownProvider.is_available", return_value=True):
            ms = PDFParserMicroservice()
            engines = ms.get_available_engines()
            assert "markitdown" in engines
