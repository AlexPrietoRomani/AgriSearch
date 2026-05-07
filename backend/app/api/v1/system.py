"""
Archivo: system.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Endpoints de la API de sistema del backend de AgriSearch.
Gestiona la información a nivel de sistema, principalmente la verificación
y listado de los modelos disponibles localmente mediante Ollama.

Acciones Principales:
    - Consulta la API de Ollama para listar los modelos instalados.
    - Analiza heurísticamente si los modelos son multimodales o de embeddings.
    - Gestiona los errores de conexión con el servicio local de IA.

Estructura Interna:
    - `OllamaModel`: Modelo Pydantic que define la estructura de retorno.
    - `list_ollama_models`: Endpoint GET para obtener la lista de modelos.

Entradas / Dependencias:
    - Servicio de Ollama corriendo en `http://127.0.0.1:11434`.
    - Depende de `httpx` para realizar peticiones HTTP asíncronas.

Salidas / Efectos:
    - Retorna una lista de objetos `OllamaModel` en formato JSON.

Integración UI:
    - Proporciona la información del sistema necesaria para las pantallas de configuración
      y validación del entorno en el frontend.
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
