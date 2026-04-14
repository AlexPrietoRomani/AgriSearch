"""
AgriSearch Backend - Vector Service (Qdrant).

Handles semantic indexing and search for article chunks.
Uses Qdrant for persistence and LiteLLM/Ollama for embeddings.
"""

import logging
import re
from typing import List, Dict, Any, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

import litellm
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorService:
    """
    Manages Qdrant collections and vector search.
    """

    def __init__(self):
        self.client = QdrantClient(path=settings.vector_db_dir.absolute().as_posix())
        self.embedding_model = settings.embedding_model
        
        # Ensure model has provider prefix for LiteLLM if missing
        if not (self.embedding_model.startswith("ollama/") or 
                self.embedding_model.startswith("openai/")):
            self.embedding_model = f"ollama/{self.embedding_model}"

    async def _get_embedding(self, text: str) -> List[float]:
        """Generates embedding using LiteLLM."""
        try:
            response = await litellm.aembedding(
                model=self.embedding_model,
                input=[text],
                api_base=settings.litellm_api_base
            )
            return response.data[0]['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _get_collection_name(self, project_id: str) -> str:
        """Standardized collection name: project_<uuid>."""
        return f"project_{project_id.replace('-', '_')}"

    async def ensure_collection(self, project_id: str, vector_size: int = 768):
        """Creates collection if it doesn't exist."""
        collection_name = self._get_collection_name(project_id)
        try:
            self.client.get_collection(collection_name)
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"Creating Qdrant collection: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, 
                        distance=models.Distance.COSINE
                    )
                )
            else:
                raise

    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[Dict[str, Any]]:
        """
        Structure-aware chunking for Markdown.
        Splits by headers first, then by size if a section is too long.
        """
        chunks = []
        
        # 1. Split by headers (## or ###)
        sections = re.split(r'(^##\s+.*$|^###\s+.*$)', text, flags=re.MULTILINE)
        
        current_section_title = "Intro"
        
        for i in range(1, len(sections), 2):
            # sections[i] is the title, sections[i+1] is the content
            title = sections[i].strip("# ").strip()
            content = sections[i+1] if i+1 < len(sections) else ""
            
            # If content is too large, split by paragraphs
            if len(content) > chunk_size:
                paragraphs = content.split("\n\n")
                current_chunk = ""
                for p in paragraphs:
                    if len(current_chunk) + len(p) < chunk_size:
                        current_chunk += p + "\n\n"
                    else:
                        if current_chunk:
                            chunks.append({"content": current_chunk.strip(), "section": title})
                        current_chunk = p + "\n\n"
                if current_chunk:
                    chunks.append({"content": current_chunk.strip(), "section": title})
            else:
                chunks.append({"content": content.strip(), "section": title})
                
        # If no sections found, fallback to simple splitting
        if not chunks:
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunks.append({"content": text[start:end], "section": "General"})
                start += chunk_size - overlap
                if start >= len(text) - overlap:
                    break
        return chunks

    async def index_article(self, project_id: str, article: Any, md_content: str):
        """Chunks and indexes an article's Markdown content with full metadata."""
        collection_name = self._get_collection_name(project_id)
        
        # 1. Chunking (Structure-aware)
        chunks = self.chunk_text(md_content)
        if not chunks:
            return

        # 2. Vectorize and prepare points
        points = []
        for i, chunk_data in enumerate(chunks):
            content = chunk_data["content"]
            section = chunk_data["section"]
            
            # Skip empty chunks
            if not content.strip():
                continue
                
            vector = await self._get_embedding(content)
            
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "article_id": article.id,
                    "doi": article.doi,
                    "title": article.title,
                    "authors": article.authors,
                    "year": article.year,
                    "section": section,
                    "chunk_idx": i,
                    "content": content
                }
            ))
        
        # 3. Batch Upsert (split points if too many)
        if points:
            await self.ensure_collection(project_id, vector_size=len(points[0].vector))
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True
            )
            logger.info(f"Indexed {len(points)} chunks for article {article.id} in {collection_name}")

    async def search(self, project_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Semantic search within a project's collection."""
        collection_name = self._get_collection_name(project_id)
        
        try:
            # 1. Embed query
            query_vector = await self._get_embedding(query)
            
            # 2. Search Qdrant
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
            print(f"DEBUG: Qdrant returned {len(results)} results")
            formatted_results = []
            for r in results:
                if r.payload:
                    formatted_results.append({
                        "article_id": r.payload.get("article_id"),
                        "title": r.payload.get("title"),
                        "content": r.payload.get("content"),
                        "score": r.score
                    })
                else:
                    logger.warning(f"Point {r.id} has no payload!")
            
            return formatted_results
        except Exception as e:
            logger.error(f"Vector search failed for project {project_id}: {e}")
            return []
