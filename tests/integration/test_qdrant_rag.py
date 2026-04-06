"""
Integration tests for VectorService and Qdrant connectivity.
Validates indexing and semantic search within a project collection.
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, patch
from backend.app.services.vector_service import VectorService

@pytest.fixture
def vector_service():
    return VectorService()

@pytest.fixture
def mock_embedding():
    # Return a non-uniform 768-dim vector to avoid normalization issues
    return [i * 0.0001 for i in range(768)]

@pytest.mark.asyncio
async def test_qdrant_connectivity(vector_service):
    """Test that we can talk to Qdrant and get collections (even if empty)."""
    try:
        collections = vector_service.client.get_collections()
        assert hasattr(collections, 'collections')
    except Exception as e:
        pytest.fail(f"Could not connect to Qdrant: {e}")

@pytest.mark.asyncio
async def test_indexing_and_search(vector_service, mock_embedding):
    """Test the full indexing and search flow with mocked embeddings."""
    project_id = str(uuid.uuid4())
    article_id = "test_abc_123"
    title = "Advancements in Tomato Agronomy"
    content = "This paper discusses how tomatoes grow in diverse climates using new CNN approaches."
    
    # Mock LiteLLM embedding call
    with patch("litellm.aembedding", new_callable=AsyncMock) as mocked_embed:
        mocked_embed.return_value.data = [{"embedding": mock_embedding}]
        
        # 1. Index article
        await vector_service.index_article(
            project_id=project_id,
            article_id=article_id,
            title=title,
            md_content=content
        )
        
        # 1.b Check point count
        collection_name = vector_service._get_collection_name(project_id)
        
        # Diagnostics
        collections = vector_service.client.get_collections().collections
        print(f"DEBUG: Visible collections: {[c.name for c in collections]}")
        
        info = vector_service.client.get_collection(collection_name)
        print(f"DEBUG: Collection {collection_name} has {info.points_count} points, status: {info.status}")
        assert info.points_count > 0
        
        # 2. Search for related term
        query = "tomato growth"
        results = await vector_service.search(project_id, query, limit=5)
        
        # 3. Assertions with diagnostics
        if not results:
            # Check by ID
            points = vector_service.client.scroll(collection_name, limit=10)[0]
            if points:
                p = points[0]
                print(f"DEBUG: Found Point ID {p.id} with payload {p.payload}")
                # Try searching with its own vector directly
                res2 = vector_service.client.search(collection_name, query_vector=p.vector, limit=1) if p.vector else []
                print(f"DEBUG: Search with manual vector returned {len(res2)} results")
            
        assert len(results) > 0, f"Search returned 0 results for project {project_id}"
        assert results[0]["article_id"] == article_id
        assert "Tomato" in results[0]["title"]
        assert results[0]["score"] > 0
        
        # Cleanup: delete the test collection
        vector_service.client.delete_collection(vector_service._get_collection_name(project_id))
