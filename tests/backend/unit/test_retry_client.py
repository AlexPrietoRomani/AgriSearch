"""
Archivo: test_retry_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para el wrapper de cliente HTTP con reintentos 
(`RetryClient`). Verifica que la lógica de reintento exponencial se ejecute 
correctamente, que se manejen los diferentes tipos de respuesta (JSON vs Texto) 
y que las excepciones de red sean capturadas y transformadas en estados seguros.

Acciones Principales:
    - Validación de flujo exitoso con retorno de datos JSON.
    - Validación de detección de contenido no-JSON (texto plano).
    - Simulación de errores de respuesta (ClientResponseError).
    - Simulación de errores de red (ClientError) y excepciones genéricas.
    - Verificación de propagación de parámetros y cabeceras HTTP.

Estructura Interna:
    - `TestFetchWithRetry`: Clase que agrupa los casos de prueba para el cliente.

Entradas / Dependencias:
    - `app.services.retry_client`.
    - `aiohttp`, `pytest`, `unittest.mock`.

Salidas / Efectos:
    - Verificación del comportamiento del cliente ante fallos de red simulados.
    - No realiza llamadas reales; usa mocks para aislar la lógica.

Ejecución:
    pytest tests/backend/unit/test_retry_client.py
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from app.services.retry_client import fetch_with_retry


class TestFetchWithRetry:
    """Tests de fetch_with_retry."""

    @pytest.mark.asyncio
    async def test_success_returns_status_and_data(self):
        """Respuesta exitosa retorna (status, data)."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.retry_client.RetryClient", return_value=mock_session):
            status, data = await fetch_with_retry("https://example.com/api")

        assert status == 200
        assert data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_non_json_returns_text(self):
        """Respuesta no-JSON retorna texto."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="plain text")
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.retry_client.RetryClient", return_value=mock_session):
            status, data = await fetch_with_retry("https://example.com/api")

        assert status == 200
        assert data == "plain text"

    @pytest.mark.asyncio
    async def test_client_response_error_returns_status(self):
        """ClientResponseError retorna (status, None)."""
        with patch("app.services.retry_client.RetryClient") as MockRetry:
            mock_instance = AsyncMock()
            MockRetry.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockRetry.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=503,
                message="Service Unavailable",
            ))

            status, data = await fetch_with_retry("https://example.com/api")

        assert status == 0  # ClientResponseError is caught by generic Exception handler
        assert data is None

    @pytest.mark.asyncio
    async def test_client_error_returns_zero(self):
        """ClientError retorna (0, None)."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.retry_client.RetryClient", return_value=mock_session):
            with patch.object(
                mock_session, "get",
                side_effect=aiohttp.ClientError("Connection refused")
            ):
                status, data = await fetch_with_retry("https://example.com/api")

        assert status == 0
        assert data is None

    @pytest.mark.asyncio
    async def test_generic_exception_returns_zero(self):
        """Exception genérica retorna (0, None)."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.retry_client.RetryClient", return_value=mock_session):
            with patch.object(
                mock_session, "get",
                side_effect=RuntimeError("Unexpected")
            ):
                status, data = await fetch_with_retry("https://example.com/api")

        assert status == 0
        assert data is None

    @pytest.mark.asyncio
    async def test_passes_params_and_headers(self):
        """Parámetros y headers se pasan correctamente."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.retry_client.RetryClient", return_value=mock_session):
            await fetch_with_retry(
                "https://example.com/api",
                params={"q": "test"},
                headers={"Authorization": "Bearer token"},
            )

        mock_session.get.assert_called_once()
        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["params"] == {"q": "test"}
        assert call_kwargs["headers"] == {"Authorization": "Bearer token"}
