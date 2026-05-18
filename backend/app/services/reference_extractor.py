"""
Archivo: reference_extractor.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Servicio de extracción de referencias bibliográficas desde APIs externas
(OpenAlex, Semantic Scholar) para artículos científicos incluidos en el screening.

Este servicio alimenta el grafo de citaciones de la Fase 4 (Exploración Bibliográfica).

Acciones Principales:
    - Normalización de DOIs desde múltiples formatos.
    - Extracción de referencias desde OpenAlex (campo referenced_works).
    - Extracción de referencias desde Semantic Scholar (campo references).
    - Deduplicación de referencias entre múltiples fuentes.
    - Procesamiento batch de todos los artículos de un proyecto.

Estructura Interna:
    - `normalize_doi()`: Limpia y valida un DOI raw.
    - `ReferenceExtractor`: Clase que consulta APIs y deduplica resultados.
    - `build_reference_batch()`: Procesa todos los artículos de un proyecto.

Entradas / Dependencias:
    - `aiohttp`: Consultas HTTP asíncronas a APIs externas.
    - `SQLAlchemy async`: Persistencia en tabla article_references.
    - `app.models.article_reference.ArticleReference`: Modelo de referencia.
    - `app.models.project.Article`: Modelo de artículo.

Salidas / Efectos:
    - Lista de referencias normalizadas y deduplicadas.
    - Tabla article_references poblada con is_in_project calculado.

Ejemplo de Integración:
    from app.services.reference_extractor import ReferenceExtractor, build_reference_batch
    
    extractor = ReferenceExtractor()
    refs = await extractor.extract_references("10.1038/s41586-021-03819-2")
    
    # O procesar todo un proyecto:
    stats = await build_reference_batch(project_id, db_session)
"""

import re
import asyncio
from typing import Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article_reference import ArticleReference
from app.models.project import Article, SearchQuery


# ─── Constantes de APIs ────────────────────────────────────────────────

OPENALEX_BASE = "https://api.openalex.org"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"


# ─── Normalización de DOI ──────────────────────────────────────────────

def normalize_doi(raw_doi: str) -> Optional[str]:
    """
    Normaliza un DOI raw a formato limpio: 10.XXXX/...
    
    Maneja:
    - URLs: https://doi.org/10.1234/test → 10.1234/test
    - Prefixes: doi:10.1234/test → 10.1234/test
    - Espacios y caracteres invisibles
    - Retorna None si no parece un DOI válido
    
    Args:
        raw_doi: DOI en cualquier formato.
    
    Returns:
        DOI normalizado o None si no es válido.
    """
    if not raw_doi:
        return None
    
    doi = raw_doi.strip()
    
    # Remover URL prefixes
    doi = re.sub(r'^https?://doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'^http://dx\.doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'^doi:\s*', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'^urn:doi:', '', doi, flags=re.IGNORECASE)
    
    # Limpiar espacios y caracteres invisibles
    doi = doi.strip()
    
    # Validar formato mínimo: debe empezar con 10.
    if not doi.startswith('10.'):
        return None
    
    return doi


# ─── ReferenceExtractor ────────────────────────────────────────────────

class ReferenceExtractor:
    """
    Extrae referencias bibliográficas de APIs externas para un artículo dado.
    
    APIs soportadas:
    - OpenAlex: campo referenced_works (lista de IDs de trabajos citados)
    - Semantic Scholar: campo references (metadatos directos de referencias)
    
    Rate limiting:
    - OpenAlex: 100 req/min → 0.6s entre requests
    - Semantic Scholar: 100 req/5min → 3s entre requests
    
    Ejemplo:
        extractor = ReferenceExtractor()
        refs = await extractor.extract_references("10.1038/s41586-021-03819-2")
        # refs = [{"cited_doi": "...", "cited_title": "...", ...}, ...]
        await extractor.close()
    """
    
    def __init__(self, rate_limit_delay: float = 0.7):
        """
        Inicializa el extractor.
        
        Args:
            rate_limit_delay: Segundos de espera entre lotes de requests a OpenAlex.
        """
        self.rate_limit_delay = rate_limit_delay
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea la sesión HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session
    
    async def fetch_from_openalex(self, doi: str) -> list[dict]:
        """
        Obtiene referencias desde OpenAlex.
        
        Flujo:
        1. GET /works/doi:{doi} → obtiene referenced_works (lista de OpenAlex IDs)
        2. Para cada referenced_work, GET /works/{id} → DOI, título, autores, año
        3. Retorna lista de referencias normalizadas
        
        Args:
            doi: DOI del artículo fuente.
        
        Returns:
            Lista de dicts con campos: cited_doi, cited_title, cited_authors, cited_year.
        """
        normalized_doi = normalize_doi(doi)
        if not normalized_doi:
            return []
        
        session = await self._get_session()
        references = []
        
        # Paso 1: Obtener el work principal y sus referenced_works
        url = f"{OPENALEX_BASE}/works/doi:{normalized_doi}"
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                work = await resp.json()
        except Exception:
            return []
        
        referenced_works_ids = work.get("referenced_works", [])
        if not referenced_works_ids:
            return []
        
        # Paso 2: Obtener metadatos de cada referencia (batch con rate limiting)
        batch_size = 10
        for i in range(0, len(referenced_works_ids), batch_size):
            batch = referenced_works_ids[i:i + batch_size]
            tasks = []
            for ref_id in batch:
                tasks.append(self._fetch_openalex_work(ref_id))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict) and result.get("cited_doi"):
                    result["extraction_source"] = "openalex"
                    references.append(result)
            
            # Rate limiting entre lotes
            await asyncio.sleep(self.rate_limit_delay)
        
        return references
    
    async def _fetch_openalex_work(self, openalex_id: str) -> Optional[dict]:
        """
        Obtiene metadatos de un work individual de OpenAlex.
        
        Args:
            openalex_id: ID completo del work (ej: https://openalex.org/W1234).
        
        Returns:
            Dict con cited_doi, cited_title, cited_authors, cited_year o None.
        """
        session = await self._get_session()
        url = f"{OPENALEX_BASE}/works/{openalex_id}"
        
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None
        
        doi = data.get("doi")
        if not doi:
            return None
        
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        
        # Extraer autores (primer 5)
        authorships = data.get("authorships", [])
        authors = []
        for authorship in authorships[:5]:
            author_name = authorship.get("author", {}).get("display_name", "")
            if author_name:
                authors.append(author_name)
        
        return {
            "cited_doi": normalized,
            "cited_title": data.get("title", "") or "",
            "cited_authors": ", ".join(authors),
            "cited_year": str(data["publication_year"]) if data.get("publication_year") else None,
        }
    
    async def fetch_from_semantic_scholar(self, doi: str) -> list[dict]:
        """
        Obtiene referencias desde Semantic Scholar.
        
        GET /graph/v1/paper/DOI:{doi}?fields=references.title,references.authors,...
        
        Args:
            doi: DOI del artículo fuente.
        
        Returns:
            Lista de dicts con campos: cited_doi, cited_title, cited_authors, cited_year.
        """
        normalized_doi = normalize_doi(doi)
        if not normalized_doi:
            return []
        
        session = await self._get_session()
        url = f"{SEMANTIC_SCHOLAR_BASE}/paper/DOI:{normalized_doi}"
        params = {
            "fields": "references.title,references.authors,references.year,references.externalIds"
        }
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []
        
        references_data = data.get("references", [])
        references = []
        
        for ref in references_data:
            external_ids = ref.get("externalIds", {})
            ref_doi = external_ids.get("DOI")
            
            if not ref_doi:
                continue
            
            normalized = normalize_doi(ref_doi)
            if not normalized:
                continue
            
            authors = ref.get("authors", [])
            author_names = [a.get("name", "") for a in authors[:5] if a.get("name")]
            
            references.append({
                "cited_doi": normalized,
                "cited_title": ref.get("title", "") or "",
                "cited_authors": ", ".join(author_names),
                "cited_year": str(ref["year"]) if ref.get("year") else None,
                "extraction_source": "semantic_scholar",
            })
        
        # Semantic Scholar tiene rate limit de 100 req/5min
        await asyncio.sleep(3.0)
        
        return references
    
    async def extract_references(self, doi: str) -> list[dict]:
        """
        Orquestador: consulta ambas APIs, deduplica y retorna referencias únicas.
        
        Deduplicación:
        - Si el mismo DOI aparece en ambas fuentes, se fusiona con
          extraction_source="openalex;semantic_scholar"
        
        Args:
            doi: DOI del artículo fuente.
        
        Returns:
            Lista de referencias únicas deduplicadas por DOI.
        """
        # Consultar ambas APIs en paralelo
        openalex_refs, ss_refs = await asyncio.gather(
            self.fetch_from_openalex(doi),
            self.fetch_from_semantic_scholar(doi),
            return_exceptions=True,
        )
        
        if isinstance(openalex_refs, Exception):
            openalex_refs = []
        if isinstance(ss_refs, Exception):
            ss_refs = []
        
        # Indexar por DOI para deduplicación
        seen: dict[str, dict] = {}
        
        for ref in openalex_refs:
            doi_key = ref["cited_doi"]
            if doi_key not in seen:
                seen[doi_key] = ref
            else:
                existing_source = seen[doi_key].get("extraction_source", "")
                seen[doi_key]["extraction_source"] = f"{existing_source};semantic_scholar"
        
        for ref in ss_refs:
            doi_key = ref["cited_doi"]
            if doi_key not in seen:
                seen[doi_key] = ref
            else:
                existing_source = seen[doi_key].get("extraction_source", "")
                if "semantic_scholar" not in existing_source:
                    seen[doi_key]["extraction_source"] = f"{existing_source};semantic_scholar"
        
        return list(seen.values())
    
    async def close(self):
        """Cerrar la sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()


# ─── Batch Processing ──────────────────────────────────────────────────

async def build_reference_batch(
    project_id: str,
    db_session: AsyncSession,
) -> dict:
    """
    Extrae referencias para todos los artículos de un proyecto.
    
    Flujo:
    1. Obtener todos los artículos del proyecto
    2. Para cada artículo con DOI, extraer referencias
    3. Marcar is_in_project comparando DOIs contra artículos del proyecto
    4. Insertar en article_references (upsert con unique constraint)
    5. Retornar estadísticas
    
    Args:
        project_id: UUID del proyecto.
        db_session: Sesión async de SQLAlchemy.
    
    Returns:
        Dict con estadísticas:
        {
            "total_articles": N,
            "articles_with_dois": N,
            "total_references_extracted": N,
            "references_in_project": N,
            "references_external": N,
            "errors": N,
        }
    """
    # 1. Obtener artículos del proyecto
    stmt = (
        select(Article)
        .join(SearchQuery, Article.search_query_id == SearchQuery.id)
        .where(SearchQuery.project_id == project_id)
    )
    result = await db_session.execute(stmt)
    articles = result.scalars().all()
    
    # Construir set de DOIs del proyecto para is_in_project
    project_dois = {
        normalize_doi(a.doi) for a in articles if a.doi
    }
    
    extractor = ReferenceExtractor()
    stats = {
        "total_articles": len(articles),
        "articles_with_dois": 0,
        "total_references_extracted": 0,
        "references_in_project": 0,
        "references_external": 0,
        "errors": 0,
    }
    
    for article in articles:
        if not article.doi:
            continue
        
        normalized_doi = normalize_doi(article.doi)
        if not normalized_doi:
            continue
        
        stats["articles_with_dois"] += 1
        
        try:
            references = await extractor.extract_references(normalized_doi)
            
            for ref in references:
                ref_doi = ref["cited_doi"]
                is_in_project = ref_doi in project_dois
                
                if is_in_project:
                    stats["references_in_project"] += 1
                else:
                    stats["references_external"] += 1
                
                # Upsert: insertar o ignorar si ya existe (unique constraint)
                ref_obj = ArticleReference(
                    source_article_id=article.id,
                    cited_doi=ref_doi,
                    cited_title=ref.get("cited_title", ""),
                    cited_authors=ref.get("cited_authors", ""),
                    cited_year=ref.get("cited_year"),
                    extraction_source=ref.get("extraction_source", "unknown"),
                    is_in_project=is_in_project,
                )
                db_session.add(ref_obj)
            
            stats["total_references_extracted"] += len(references)
            
        except Exception:
            stats["errors"] += 1
            # Continuar con el siguiente artículo
    
    await db_session.commit()
    await extractor.close()
    
    return stats
