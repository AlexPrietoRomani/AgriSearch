"""
Archivo: retry_client.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Cliente HTTP asíncrono con soporte nativo para reintentos (retries) exponenciales.
Diseñado para ser utilizado por todos los clientes de bases de datos científicas
y así manejar de forma robusta errores temporales como Rate Limits (429) o
caídas de servidor (503, 502, 504).

Acciones Principales:
    - Realiza peticiones GET con política de reintento configurable.
    - Maneja automáticamente el backoff exponencial.
    - Detecta y extrae respuestas tanto en formato JSON como en texto plano.

Estructura Interna:
    - `fetch_with_retry`: Función principal asíncrona para la ejecución de peticiones.

Entradas / Dependencias:
    - `aiohttp_retry`: Para la lógica de reintento.
    - `aiohttp`: Cliente HTTP base.

Salidas / Efectos:
    - Retorna una tupla `(status_code: int, data: Any | None)`.
    - Ejecuta múltiples peticiones HTTP en caso de fallos controlados.

Ejemplo de Integración:
    from app.services.retry_client import fetch_with_retry
    status, data = await fetch_with_retry("https://api.example.com/data")
"""

import logging
from typing import Any

import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry

logger = logging.getLogger(__name__)

DEFAULT_RETRY = ExponentialRetry(
    attempts=3,
    start_timeout=0.5,
    max_timeout=10.0,
    factor=2.0,
    statuses={429, 503, 502, 504},
    retry_all_server_errors=True,
)


async def fetch_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    retry_options: ExponentialRetry | None = None,
    timeout: int = 30,
) -> tuple[int, Any]:
    """
    Realiza una petición GET asíncrona con política de reintento exponencial.

    Args:
        url (str): URL del endpoint a consultar.
        params (dict, opcional): Parámetros de consulta (query string).
        headers (dict, opcional): Cabeceras HTTP de la petición.
        retry_options (ExponentialRetry, opcional): Configuración de reintento personalizada.
        timeout (int): Tiempo de espera máximo en segundos. Por defecto es 30.

    Returns:
        tuple[int, Any]: Una tupla conteniendo (código_estado, datos_respuesta).
        Si ocurre un error fatal o se agotan los reintentos, el código será 0 o el 
        último status HTTP recibido, y los datos serán None.
    """
    retry = retry_options or DEFAULT_RETRY
    try:
        async with RetryClient(retry_options=retry) as client:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with client.get(
                url, params=params, headers=headers, timeout=timeout_obj
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    return resp.status, await resp.json()
                else:
                    return resp.status, await resp.text()
    except aiohttp.ClientResponseError as e:
        logger.warning("HTTP %d después de retries: %s", e.status, url)
        return e.status, None
    except aiohttp.ClientError as e:
        logger.warning("Error de red en %s: %s", url, e)
        return 0, None
    except Exception as e:
        logger.error("Error inesperado en %s: %s", url, e)
        return 0, None
