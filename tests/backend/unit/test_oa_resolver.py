"""
Archivo: test_oa_resolver.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para el servicio de resolución de URLs Open Access 
(`OAResolver`). Valida la integración con la API de Unpaywall mediante mocks, 
el manejo de fallbacks de URLs, el comportamiento del sistema de caché (aciertos, 
errores y limpieza) y la robustez ante fallos de red o tiempos de espera.

Acciones Principales:
    - Validación de resoluciones exitosas (PDF vs Landing page).
    - Verificación del comportamiento del caché (TTL, negativos, limpieza).
    - Simulación de errores HTTP (404, 500, ClientError, Timeouts).
    - Pruebas de casos borde (inputs nulos o vacíos).

Estructura Interna:
    - `TestResolveOaUrlSuccess`: Pruebas de flujo positivo.
    - `TestResolveOaUrlCaching`: Pruebas de eficiencia y persistencia en memoria.
    - `TestResolveOaUrlErrors`: Pruebas de tolerancia a fallos.

Entradas / Dependencias:
    - `app.services.oa_resolver`: Componente bajo prueba.
    - `aiohttp`, `pytest`, `unittest.mock`.

Salidas / Efectos:
    - Reporte detallado de cobertura de casos de éxito y fallo en consola.
    - Limpieza automática del caché en memoria entre ejecuciones de tests.

Ejecución:
    pytest tests/backend/unit/test_oa_resolver.py
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.oa_resolver import resolve_oa_url, clear_cache, _cache


@pytest.fixture(autouse=True)
def clean_cache():
    """Limpia el caché antes de cada test."""
    clear_cache()
    yield
    clear_cache()


class TestResolveOaUrlSuccess:
    """Tests de resolución exitosa."""

    @pytest.mark.asyncio
    async def test_resolve_oa_url_success(self):
        """Mock de Unpaywall 200 con best_oa_location retorna PDF URL."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "best_oa_location": {
                "url_for_pdf": "https://example.com/paper.pdf",
                "url": "https://example.com/paper/landing",
            }
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result == "https://example.com/paper.pdf"

    @pytest.mark.asyncio
    async def test_resolve_oa_url_fallback_to_url(self):
        """Si url_for_pdf no existe, usa url (landing page)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "best_oa_location": {
                "url_for_pdf": None,
                "url": "https://example.com/paper/landing",
            }
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result == "https://example.com/paper/landing"

    @pytest.mark.asyncio
    async def test_resolve_oa_url_no_oa_location(self):
        """Si best_oa_location es None, retorna None."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "best_oa_location": None
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result is None


class TestResolveOaUrlEdgeCases:
    """Tests de casos borde."""

    @pytest.mark.asyncio
    async def test_resolve_oa_url_empty_doi(self):
        """DOI vacío retorna None."""
        result = await resolve_oa_url("", "test@email.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_oa_url_none_doi(self):
        """DOI None retorna None."""
        result = await resolve_oa_url(None, "test@email.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_oa_url_empty_email(self):
        """Email vacío retorna None sin hacer llamada HTTP."""
        result = await resolve_oa_url("10.1234/test", "")
        assert result is None


class TestResolveOaUrlCaching:
    """Tests de caché."""

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self):
        """Segunda llamada usa caché sin hacer HTTP."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            # Primera llamada - hace HTTP
            result1 = await resolve_oa_url("10.1234/test", "test@email.com")
            # Segunda llamada - usa caché
            result2 = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result1 == result2
        # Session.get solo se llamó una vez (la segunda usa caché)
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_negative_result(self):
        """El resultado negativo (None) también se cachea."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result1 = await resolve_oa_url("10.1234/test", "test@email.com")
            result2 = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result1 is None
        assert result2 is None
        assert mock_session.get.call_count == 1

    def test_clear_cache_works(self):
        """clear_cache limpia el caché."""
        _cache["test:10.1234"] = (0.0, "https://example.com")
        clear_cache()
        assert len(_cache) == 0


class TestResolveOaUrlErrors:
    """Tests de manejo de errores."""

    @pytest.mark.asyncio
    async def test_resolve_oa_url_http_error(self):
        """Error de red retorna None."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_oa_url_timeout(self):
        """Timeout retorna None."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_oa_url_server_error_500(self):
        """Server error 500 retorna None (no se cachea)."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.oa_resolver.aiohttp.ClientSession", return_value=mock_session):
            result = await resolve_oa_url("10.1234/test", "test@email.com")

        assert result is None
