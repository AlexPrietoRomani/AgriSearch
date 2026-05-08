"""
Archivo: system.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Endpoints de gestión del sistema para AgriSearch. Proporciona información sobre el
estado de los servicios locales (Ollama) y la configuración de las bases de datos
científicas externas. Esencial para la validación del entorno y la configuración
del usuario en el frontend.

Acciones Principales:
    - `list_ollama_models`: Recupera y clasifica los modelos de IA locales.
    - `db_status`: Verifica la disponibilidad y requerimientos de las fuentes de datos.

Estructura Interna:
    - `OllamaModel`: Esquema para modelos locales.
    - `DBStatus`: Esquema para el estado de las APIs científicas.

Entradas / Dependencias:
    - Ollama API (localhost:11434).
    - `app.core.config.Settings`: Para verificar la presencia de API keys.

Salidas / Efectos:
    - Retorna el estado de conectividad con servicios de IA locales.
    - Expone metadatos de configuración de APIs externas (sin revelar claves).

Integración UI:
    - Consumido por el Dashboard y las pantallas de Configuración.
"""

import logging
import httpx
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])

class OllamaModel(BaseModel):
    """
    Modelo de datos para representar un modelo descargado de Ollama.
    """
    name: str
    size: float
    is_multimodal: bool
    is_embedding: bool

class DBStatus(BaseModel):
    """Estado de una base de datos científica."""
    id: str
    label: str
    requires_key: bool
    key_configured: bool
    downloadable: bool
    note: str

@router.get("/ollama-models", response_model=List[OllamaModel], summary="List available Ollama models")
async def list_ollama_models() -> List[OllamaModel]:
    """
    Obtiene la lista de modelos de Ollama descargados localmente.

    Realiza una petición a la API local de Ollama para recuperar los tags de los modelos,
    y utiliza heurísticas basadas en el nombre y la familia del modelo para determinar
    si soporta modalidades visuales (multimodal) o si se trata de un modelo de embeddings.

    Returns:
        List[OllamaModel]: Lista de los modelos detectados y sus propiedades.

    Raises:
        HTTPException: Si el servicio de Ollama no responde (503) o si ocurre otro error (500).
    """
    try:
        # Se utiliza httpx para evitar el bloqueo síncrono que generaría la librería de ollama
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://127.0.0.1:11434/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                details = m.get("details", {})
                families = details.get("families", [])
                format = details.get("format", "")
                
                # Heurística para multimodal: la familia contiene "clip" o "vision", o el nombre incluye palabras clave
                is_multimodal = "clip" in families or "vision" in name.lower() or "llava" in name.lower() or "gemma4:e4b" in name.lower()
                
                # Heurística para embedding: el nombre contiene "embed"
                is_embedding = "embed" in name.lower()
                
                models.append(OllamaModel(
                    name=name,
                    size=m.get("size", 0) / (1024 * 1024 * 1024), # Conversión a GB
                    is_multimodal=is_multimodal,
                    is_embedding=is_embedding
                ))
            return models
    except httpx.RequestError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        raise HTTPException(status_code=503, detail="Ollama local service is not running or unreachable.")
    except Exception as e:
        logger.error(f"Error listing Ollama models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db-status", response_model=Dict[str, DBStatus], summary="Database availability status")
async def db_status() -> Dict[str, DBStatus]:
    """
    Retorna el estado de cada base de datos científica.

    Indica si cada BD requiere API key, si está configurada,
    y si permite descarga automática de PDFs.
    """
    from app.core.config import get_settings
    settings = get_settings()

    return {
        "openalex": DBStatus(
            id="openalex", label="OpenAlex",
            requires_key=False, key_configured=True, downloadable=True,
            note=">200M works, OA incluido"
        ),
        "semantic_scholar": DBStatus(
            id="semantic_scholar", label="Semantic Scholar",
            requires_key=False, key_configured=True, downloadable=True,
            note="AI-powered, 200M+ papers"
        ),
        "arxiv": DBStatus(
            id="arxiv", label="ArXiv",
            requires_key=False, key_configured=True, downloadable=True,
            note="Preprints, siempre OA"
        ),
        "crossref": DBStatus(
            id="crossref", label="Crossref",
            requires_key=False, key_configured=True, downloadable=False,
            note="Solo DOIs — requiere Unpaywall/Sci-Hub para PDF"
        ),
        "core": DBStatus(
            id="core", label="CORE",
            requires_key=True, key_configured=bool(settings.core_api_key),
            downloadable=True, note="Open Access repository"
        ),
        "scielo": DBStatus(
            id="scielo", label="SciELO",
            requires_key=False, key_configured=True, downloadable=True,
            note="Latinoamérica, español/portugués"
        ),
        "redalyc": DBStatus(
            id="redalyc", label="Redalyc",
            requires_key=True, key_configured=bool(settings.redalyc_token),
            downloadable=True, note="Iberoamérica, requiere token gratuito"
        ),
        "agecon": DBStatus(
            id="agecon", label="AgEcon Search",
            requires_key=False, key_configured=True, downloadable=True,
            note="Economía agrícola, OAI-PMH"
        ),
        "organic_eprints": DBStatus(
            id="organic_eprints", label="Organic Eprints",
            requires_key=False, key_configured=True, downloadable=True,
            note="Agricultura orgánica, OAI-PMH"
        ),
    }
