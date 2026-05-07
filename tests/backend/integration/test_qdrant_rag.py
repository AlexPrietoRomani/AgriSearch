"""
Archivo: test_qdrant_rag.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas de integración para `VectorService` y la conectividad con Qdrant.
Valida el ciclo de vida completo de la información en el motor vectorial:
indexación de fragmentos de artículos y búsqueda semántica dentro de 
colecciones específicas por proyecto.

Acciones Principales:
    - Verificación de la conectividad básica con el servidor Qdrant.
    - Simulación (mocking) de embeddings de LiteLLM para pruebas aisladas.
    - Indexación de contenido Markdown en colecciones temporales.
    - Ejecución de búsquedas semánticas y validación de la relevancia de los resultados.
    - Limpieza automática de colecciones de prueba después de cada ejecución.

Entradas / Dependencias:
    - Instancia activa de Qdrant (Docker o Cloud).
    - `VectorService` del backend.
    - Mock de `litellm.aembedding`.

Ejemplo de Ejecución:
    pytest tests/backend/integration/test_qdrant_rag.py
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.vector_service import VectorService


@pytest.fixture
def vector_service() -> VectorService:
    """Retorna una instancia del servicio de vectores para pruebas."""
    return VectorService()


@pytest.fixture
def mock_embedding() -> list:
    """Retorna un vector de 768 dimensiones no uniforme para simular un embedding."""
    return [i * 0.0001 for i in range(768)]


@pytest.mark.asyncio
async def test_qdrant_connectivity(vector_service: VectorService):
    """
    Verifica que la conexión con el servidor Qdrant sea exitosa.
    """
    try:
        collections = vector_service.client.get_collections()
        assert hasattr(collections, 'collections')
    except Exception as e:
        pytest.fail(f"No se pudo conectar a Qdrant: {e}")


@pytest.mark.asyncio
async def test_indexing_and_search(vector_service: VectorService, mock_embedding: list):
    """
    Valida el flujo completo de indexación y búsqueda semántica.
    """
    project_id = str(uuid.uuid4())
    article_id = "test_abc_123"
    title = "Advancements in Tomato Agronomy"
    content = "This paper discusses how tomatoes grow in diverse climates using new CNN approaches."
    
    # Mock de la llamada a LiteLLM para generar embeddings
    with patch("litellm.aembedding", new_callable=AsyncMock) as mocked_embed:
        mocked_embed.return_value.data = [{"embedding": mock_embedding}]
        
        # 1. Indexar artículo
        await vector_service.index_article(
            project_id=project_id,
            article_id=article_id,
            title=title,
            md_content=content
        )
        
        # 2. Verificar existencia de la colección y puntos
        collection_name = vector_service._get_collection_name(project_id)
        info = vector_service.client.get_collection(collection_name)
        assert info.points_count > 0
        
        # 3. Ejecutar búsqueda semántica
        query = "tomato growth"
        results = await vector_service.search(project_id, query, limit=5)
        
        # 4. Validar resultados
        assert len(results) > 0, f"La búsqueda retornó 0 resultados para el proyecto {project_id}"
        assert results[0]["article_id"] == article_id
        assert "Tomato" in results[0]["title"]
        assert results[0]["score"] > 0
        
        # 5. Limpieza: eliminar la colección de prueba
        vector_service.client.delete_collection(vector_service._get_collection_name(project_id))
