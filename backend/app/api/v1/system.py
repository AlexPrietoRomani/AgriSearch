"""
AgriSearch Backend - System API endpoints.

Handles system-level information like available Ollama models.
"""

import logging
import httpx
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])

class OllamaModel(BaseModel):
    name: str
    size: float
    is_multimodal: bool
    is_embedding: bool

@router.get("/ollama-models", response_model=List[OllamaModel], summary="List available Ollama models")
async def list_ollama_models():
    """Get the list of locally downloaded Ollama models."""
    try:
        # We can either use ollama package or httpx to directly query the API
        # Using httpx to avoid synchronous blocking of the ollama library
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
                
                # Heuristic for multimodal: family contains "clip" or "vision" or name has vision keywords
                is_multimodal = "clip" in families or "vision" in name.lower() or "llava" in name.lower() or "gemma4:e4b" in name.lower()
                
                # Heuristic for embedding: name contains embed or 
                is_embedding = "embed" in name.lower()
                
                models.append(OllamaModel(
                    name=name,
                    size=m.get("size", 0) / (1024 * 1024 * 1024), # GB
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
