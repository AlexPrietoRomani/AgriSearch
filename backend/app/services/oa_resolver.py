"""
Archivo: oa_resolver.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Servicio de resolución de URLs de acceso abierto (Open Access) utilizando la API
de Unpaywall. Permite obtener enlaces directos a PDFs para artículos que solo
poseen DOI (como los provenientes de Crossref).

Acciones Principales:
    - Consulta la API de Unpaywall para obtener la mejor ubicación OA.
    - Implementa una caché en memoria con TTL de 24 horas para optimizar el rendimiento.
    - Maneja fallbacks para DOIs sin disponibilidad de acceso abierto.

Estructura Interna:
    - `resolve_oa_url`: Función asíncrona principal de resolución.
    - `clear_cache`: Utilidad para limpieza de caché.

Entradas / Dependencias:
    - `aiohttp`: Para peticiones HTTP asíncronas.
    - API de Unpaywall (v2).

Salidas / Efectos:
    - Retorna la URL del PDF o landing page resuelta (str | None).
    - Mantiene un diccionario de caché global en memoria (`_cache`).

Ejemplo de Integración:
    from app.services.oa_resolver import resolve_oa_url
    oa_url = await resolve_oa_url("10.1234/example", "admin@agrisearch.ai")
"""

import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

# Cache simple en memoria con TTL
_cache: dict[str, tuple[float, Optional[str]]] = {}
_CACHE_TTL = 86400  # 24 horas


async def resolve_oa_url(doi: str, email: str) -> Optional[str]:
    """Intenta resolver OA URL desde Unpaywall para un DOI dado.

    Usa caché en memoria con TTL de 24h para no exceder
    el rate limit de Unpaywall (gratuito, sin API key).

    Args:
        doi: Identificador DOI del artículo (ej. "10.1234/example").
        email: Email registrado para acceder a la API de Unpaywall.

    Returns:
        URL del PDF/landing page OA, o None si no se encontró.
    """
    if not doi:
        return None

    if not email:
        logger.debug("Unpaywall: sin email configurado, saltando resolución para %s", doi)
        return None

    # Verificar caché
    now = asyncio.get_event_loop().time()
    if doi in _cache:
        cached_time, cached_result = _cache[doi]
        if now - cached_time < _CACHE_TTL:
            return cached_result

    # Consultar Unpaywall
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    best = data.get("best_oa_location") or {}
                    oa_url = best.get("url_for_pdf") or best.get("url")
                    _cache[doi] = (now, oa_url)
                    if oa_url:
                        logger.debug("Unpaywall OA resuelto: %s -> %s", doi, oa_url[:80])
                    else:
                        logger.debug("Unpaywall: sin OA para %s", doi)
                    return oa_url
                elif resp.status == 404:
                    _cache[doi] = (now, None)  # Cachear negativos también
                    return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning("Unpaywall error para %s: %s", doi, e)
        return None


def clear_cache():
    """Limpia el caché de resoluciones OA. Útil para tests."""
    _cache.clear()
