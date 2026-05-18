"""
Archivo: graph_service.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Servicios de construcción de grafos bibliográficos para AgriSearch.

Contiene:
- CitationGraphBuilder: Grafo dirigido de citaciones (A cita a B)
- Funciones auxiliares de serialización y carga

El grafo de citaciones usa NetworkX para construir un grafo dirigido donde:
- Nodos verdes: artículos incluidos en el proyecto
- Nodos azules: artículos externos citados pero no incluidos
- Aristas dirigidas: A → B significa "A cita a B"

Acciones Principales:
    - Cargar artículos y referencias desde la BD.
    - Construir grafo dirigido con NetworkX.
    - Calcular métricas (in-degree, artículos puente, densidad).
    - Serializar a formato vis-network compatible.
    - Guardar/cargar grafos como JSON en disco.
    - Obtener vecinos de un nodo con profundidad configurable.

Entradas / Dependencias:
    - `networkx`: Construcción y manipulación de grafos.
    - `sqlalchemy`: Consultas a tablas articles y article_references.
    - `app.models.project.Article`: Modelo de artículo.
    - `app.models.article_reference.ArticleReference`: Modelo de referencia.
    - `app.services.reference_extractor.normalize_doi`: Normalización de DOIs.

Salidas / Efectos:
    - Grafo NetworkX DiGraph en memoria.
    - Archivo JSON en data/projects/{project_id}/graphs/citation_graph.json.
    - Métricas calculadas (top citados, artículos puente, densidad).

Ejemplo de Integración:
    from app.services.graph_service import CitationGraphBuilder
    
    builder = CitationGraphBuilder(db_session, project_id="uuid-123")
    G = await builder.build_directed_graph()
    metrics = builder.calculate_metrics()
    path = builder.save_graph()
    
    # Cargar grafo existente:
    data = CitationGraphBuilder.load_graph("uuid-123")
    
    # Obtener vecinos:
    neighbors = builder.get_neighbors("10.1038/s41586-021-03819-2", depth=1)
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional

import networkx as nx
from numpy.typing import NDArray
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Article, SearchQuery, ScreeningDecision
from app.models.article_reference import ArticleReference
from app.services.reference_extractor import normalize_doi


# ─── Filtro estricto de artículos para grafos ──────────────────────────

async def has_screening_decisions(
    project_id: str,
    db_session: AsyncSession,
) -> bool:
    """
    Verifica si existen decisiones de screening para un proyecto.
    
    Args:
        project_id: UUID del proyecto.
        db_session: Sesión async de SQLAlchemy.
    
    Returns:
        True si hay al menos una decisión de screening, False en caso contrario.
    """
    stmt = (
        select(ScreeningDecision)
        .join(Article, ScreeningDecision.article_id == Article.id)
        .join(SearchQuery, Article.search_query_id == SearchQuery.id)
        .where(SearchQuery.project_id == project_id)
        .limit(1)
    )
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_eligible_articles_for_graphs(
    project_id: str,
    db_session: AsyncSession,
    screening_status: str = "included",
) -> list[Article]:
    """
    Obtiene artículos elegibles para grafos con filtros estrictos.
    
    Criterios estrictos (siempre aplicados):
    1. doi IS NOT NULL y empieza con '10.'
    2. download_status = 'SUCCESS'
    3. local_md_path IS NOT NULL
    4. parsed_status = 'success'
    
    Filtro de screening (opcional):
    - "included": solo ScreeningDecision.decision = 'include'
    - "maybe": solo ScreeningDecision.decision = 'maybe'
    - "all": sin filtro de screening (solo filtros estrictos)
    
    Args:
        project_id: UUID del proyecto.
        db_session: Sesión async de SQLAlchemy.
        screening_status: "included" (default), "maybe", o "all".
    
    Returns:
        Lista de Article que cumplen todos los criterios.
    """
    # Query base con filtros estrictos
    base_query = (
        select(Article)
        .join(SearchQuery, Article.search_query_id == SearchQuery.id)
        .where(
            SearchQuery.project_id == project_id,
            Article.doi.isnot(None),
            Article.download_status == "SUCCESS",
            Article.local_md_path.isnot(None),
            Article.parsed_status == "success",
        )
    )
    
    # Aplicar filtro de screening si no es "all"
    if screening_status != "all":
        decision_value = "include" if screening_status == "included" else "maybe"
        base_query = (
            base_query
            .join(ScreeningDecision, ScreeningDecision.article_id == Article.id)
            .where(ScreeningDecision.decision == decision_value)
        )
    
    result = await db_session.execute(base_query)
    return list(result.scalars().all())


# ─── Colores para vis-network ──────────────────────────────────────────

COLOR_INCLUDED = "#22c55e"       # Verde
COLOR_EXTERNAL = "#3b82f6"       # Azul
COLOR_BORDER_INCLUDED = "#16a34a"
COLOR_BORDER_EXTERNAL = "#2563eb"


# ─── CitationGraphBuilder ──────────────────────────────────────────────

class CitationGraphBuilder:
    """
    Construye un grafo dirigido de citaciones bibliográficas.
    
    Nodos:
    - Artículos incluidos (verde): existen en el proyecto
    - Artículos externos (azul): citados pero no descargados
    
    Aristas:
    - Dirigidas: A → B significa "A cita a B"
    
    Ejemplo:
        builder = CitationGraphBuilder(db_session, project_id)
        G = await builder.build_directed_graph()
        metrics = builder.calculate_metrics()
        builder.save_graph()
    """
    
    def __init__(self, db_session: AsyncSession, project_id: str):
        """
        Inicializa el builder.
        
        Args:
            db_session: Sesión async de SQLAlchemy.
            project_id: UUID del proyecto.
        """
        self.db_session = db_session
        self.project_id = project_id
        self.graph: Optional[nx.DiGraph] = None
    
    async def load_project_articles(self, screening_status: str = "included") -> dict[str, dict]:
        """
        Carga artículos del proyecto con filtros estrictos + screening.
        
        Args:
            screening_status: "included" (default), "maybe", o "all".
        
        Returns:
            Dict {doi_normalized: {title, authors, year, article_id, abstract, doi_original}}
        """
        articles = await get_eligible_articles_for_graphs(
            self.project_id, self.db_session, screening_status
        )
        
        articles_map = {}
        for article in articles:
            if article.doi:
                normalized = normalize_doi(article.doi)
                if normalized:
                    articles_map[normalized] = {
                        "doi": normalized,
                        "title": article.title or "",
                        "authors": article.authors or "",
                        "year": str(article.year) if article.year else "",
                        "article_id": article.id,
                        "abstract": article.abstract or "",
                    }
        
        return articles_map
    
    async def load_references(self, screening_status: str = "included") -> list[dict]:
        """
        Carga referencias del proyecto filtradas por screening_status.
        
        Las referencias se filtran para incluir solo aquellas cuyo artículo
        fuente cumple con el screening_status especificado.
        
        Args:
            screening_status: "included" (default), "maybe", o "all".
        
        Returns:
            Lista de dicts con referencias.
        """
        eligible_articles = await get_eligible_articles_for_graphs(
            self.project_id, self.db_session, screening_status
        )
        eligible_ids = {a.id for a in eligible_articles}
        
        if not eligible_ids:
            return []
        
        stmt = select(ArticleReference).where(
            ArticleReference.source_article_id.in_(eligible_ids)
        )
        result = await self.db_session.execute(stmt)
        refs = result.scalars().all()
        
        return [
            {
                "source_article_id": ref.source_article_id,
                "cited_doi": ref.cited_doi,
                "cited_title": ref.cited_title,
                "cited_authors": ref.cited_authors,
                "cited_year": ref.cited_year,
                "is_in_project": ref.is_in_project,
                "extraction_source": ref.extraction_source,
            }
            for ref in refs
        ]
    
    async def build_directed_graph(self, screening_status: str = "included") -> nx.DiGraph:
        """
        Construye el grafo dirigido de citaciones con filtros estrictos.
        
        Args:
            screening_status: "included" (default), "maybe", o "all".
        
        Flujo:
        1. Cargar artículos elegibles (nodos verdes)
        2. Cargar referencias filtradas
        3. Crear nodos para artículos elegibles
        4. Crear nodos para artículos externos citados
        5. Crear aristas dirigidas (source → cited)
        6. Calcular métricas (in-degree, bridge articles)
        
        Returns:
            Grafo NetworkX DiGraph construido.
        """
        articles_map = await self.load_project_articles(screening_status)
        references = await self.load_references(screening_status)
        
        G = self._build_graph_from_data(articles_map, references)
        self.graph = G
        return G
    
    def _build_graph_from_data(self, articles_map: dict[str, dict], references: list[dict]) -> nx.DiGraph:
        """
        Construye el grafo a partir de datos ya cargados (útil para testing).
        
        Args:
            articles_map: Dict {doi: {title, authors, year, article_id, abstract}}
            references: Lista de dicts con referencias.
        
        Returns:
            Grafo NetworkX DiGraph construido.
        """
        G = nx.DiGraph()
        
        # Paso 1: Añadir nodos de artículos incluidos (verde)
        for doi, meta in articles_map.items():
            short_label = self._make_label(meta["authors"], meta["year"])
            G.add_node(
                doi,
                status="included",
                label=short_label,
                title=meta["title"],
                authors=meta["authors"],
                year=meta["year"],
                article_id=meta["article_id"],
                abstract=meta["abstract"],
                color={
                    "background": COLOR_INCLUDED,
                    "border": COLOR_BORDER_INCLUDED,
                    "highlight": {"background": "#4ade80", "border": "#15803d"},
                },
                shape="dot",
                size=20,
            )
        
        # Paso 2: Añadir nodos de artículos externos (azul) y aristas
        external_citation_count: dict[str, int] = {}
        
        for ref in references:
            cited_doi = ref["cited_doi"]
            source_doi = None
            
            for doi, meta in articles_map.items():
                if meta["article_id"] == ref["source_article_id"]:
                    source_doi = doi
                    break
            
            if not source_doi:
                continue
            
            # Si el citado no está en el proyecto y no existe aún, crear nodo externo
            # IMPORTANTE: crear ANTES de add_edge para que no se cree sin atributos
            if not ref["is_in_project"] and cited_doi not in G:
                short_label = self._make_label(ref["cited_authors"], ref["cited_year"] or "?")
                G.add_node(
                    cited_doi,
                    status="cited_external",
                    label=short_label,
                    title=ref["cited_title"],
                    authors=ref["cited_authors"],
                    year=ref["cited_year"] or "",
                    article_id=None,
                    abstract="",
                    color={
                        "background": COLOR_EXTERNAL,
                        "border": COLOR_BORDER_EXTERNAL,
                        "highlight": {"background": "#60a5fa", "border": "#1d4ed8"},
                    },
                    shape="dot",
                    size=12,
                )
                external_citation_count[cited_doi] = 0
            
            # Crear arista dirigida: source → cited
            G.add_edge(
                source_doi,
                cited_doi,
                arrows="to",
                extraction_source=ref["extraction_source"],
            )
            
            external_citation_count[cited_doi] = external_citation_count.get(cited_doi, 0) + 1
        
        # Paso 3: Calcular in-degree y ajustar tamaños
        in_degrees = dict(G.in_degree())
        max_degree = max(in_degrees.values()) if in_degrees else 1
        
        for node in G.nodes():
            degree = in_degrees.get(node, 0)
            size = 10 + (degree / max(max_degree, 1)) * 30
            G.nodes[node]["size"] = size
            G.nodes[node]["in_degree"] = degree
        
        # Paso 4: Marcar artículos puente (externos citados por ≥2 incluidos)
        for node in G.nodes():
            if G.nodes[node]["status"] == "cited_external":
                G.nodes[node]["is_bridge"] = external_citation_count.get(node, 0) >= 2
        
        return G
    
    def _make_label(self, authors: str, year: str) -> str:
        """Crea un label corto para vis-network."""
        if not authors:
            return f"Unknown ({year})"
        first_author = authors.split(",")[0].strip()
        if len(first_author) > 25:
            first_author = first_author[:22] + "..."
        return f"{first_author} ({year})"
    
    def calculate_metrics(self) -> dict:
        """
        Calcula métricas del grafo.
        
        Returns:
            Dict con: total_nodes, total_edges, total_included, total_external,
            most_cited (top 5), bridge_articles, density.
        """
        if self.graph is None:
            return {}
        
        G = self.graph
        in_degrees = dict(G.in_degree())
        
        sorted_by_degree = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)
        most_cited = []
        for doi, degree in sorted_by_degree[:5]:
            most_cited.append({
                "doi": doi,
                "title": G.nodes[doi].get("title", ""),
                "in_degree": degree,
            })
        
        bridge_articles = [
            {
                "doi": node,
                "title": G.nodes[node].get("title", ""),
                "cited_by_count": in_degrees.get(node, 0),
            }
            for node in G.nodes()
            if G.nodes[node].get("status") == "cited_external"
            and G.nodes[node].get("is_bridge", False)
        ]
        
        total_included = sum(
            1 for n in G.nodes() if G.nodes[n]["status"] == "included"
        )
        total_external = sum(
            1 for n in G.nodes() if G.nodes[n]["status"] == "cited_external"
        )
        
        return {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "total_included": total_included,
            "total_external": total_external,
            "most_cited": most_cited,
            "bridge_articles": bridge_articles,
            "density": nx.density(G),
        }
    
    def serialize_to_vis_network(self) -> dict:
        """
        Serializa el grafo a formato compatible con vis-network.
        
        Returns:
            Dict con {nodes: [...], edges: [...], metadata: {...}}
        """
        if self.graph is None:
            return {"nodes": [], "edges": [], "metadata": {}}
        
        G = self.graph
        nodes = []
        edges = []
        
        for node, data in G.nodes(data=True):
            nodes.append({
                "id": node,
                "label": data.get("label", node),
                "title": data.get("title", ""),
                "color": data.get("color", {}),
                "size": data.get("size", 15),
                "shape": data.get("shape", "dot"),
                "status": data.get("status", "unknown"),
            })
        
        for source, target, data in G.edges(data=True):
            edges.append({
                "from": source,
                "to": target,
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            })
        
        metadata = self.calculate_metrics()
        
        return {
            "graph_type": "citation",
            "project_id": self.project_id,
            "nodes": nodes,
            "edges": edges,
            "metadata": metadata,
        }
    
    def save_graph(self, graph_dir: Optional[Path] = None, suffix: str = "included") -> Path:
        """
        Guarda el grafo serializado como JSON en disco.
        
        Args:
            graph_dir: Directorio donde guardar. Default: data/projects/{id}/graphs/
            suffix: Suffix para el archivo (screening_status). Default: "included"
        
        Returns:
            Ruta del archivo JSON guardado.
        """
        if self.graph is None:
            raise ValueError("No hay grafo construido. Llama a build_directed_graph() primero.")
        
        if graph_dir is None:
            graph_dir = Path(f"data/projects/{self.project_id}/graphs")
        
        graph_dir.mkdir(parents=True, exist_ok=True)
        output_path = graph_dir / f"citation_graph_{suffix}.json"
        
        data = self.serialize_to_vis_network()
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        
        return output_path
    
    @staticmethod
    def load_graph(project_id: str, graph_dir: Optional[Path] = None, suffix: str = "included") -> Optional[dict]:
        """
        Carga un grafo previamente guardado desde JSON.
        
        Args:
            project_id: UUID del proyecto.
            graph_dir: Directorio del grafo. Default: data/projects/{id}/graphs/
            suffix: Suffix del archivo (screening_status). Default: "included"
        
        Returns:
            Dict con nodos y aristas, o None si no existe.
        """
        if graph_dir is None:
            graph_dir = Path(f"data/projects/{project_id}/graphs")
        
        json_path = graph_dir / f"citation_graph_{suffix}.json"
        if not json_path.exists():
            return None
        
        return json.loads(json_path.read_text(encoding="utf-8"))
    
    def get_neighbors(self, doi: str, depth: int = 1) -> dict:
        """
        Obtiene los vecinos de un nodo específico.
        
        Args:
            doi: DOI del nodo.
            depth: Profundidad de expansión (default: 1).
        
        Returns:
            Dict con nodos vecinos y aristas conectadas.
        """
        if self.graph is None:
            return {"nodes": [], "edges": []}
        
        if doi not in self.graph:
            return {"nodes": [], "edges": []}
        
        neighbors = set()
        edges_to_include = []
        
        if depth == 1:
            for neighbor in self.graph.predecessors(doi):
                neighbors.add(neighbor)
                edges_to_include.append((neighbor, doi))
            for neighbor in self.graph.successors(doi):
                neighbors.add(neighbor)
                edges_to_include.append((doi, neighbor))
        else:
            visited = {doi}
            current_level = {doi}
            for _ in range(depth):
                next_level = set()
                for node in current_level:
                    for neighbor in self.graph.predecessors(node):
                        if neighbor not in visited:
                            next_level.add(neighbor)
                            edges_to_include.append((neighbor, node))
                    for neighbor in self.graph.successors(node):
                        if neighbor not in visited:
                            next_level.add(neighbor)
                            edges_to_include.append((node, neighbor))
                visited.update(next_level)
                neighbors.update(next_level)
                current_level = next_level
        
        nodes = []
        for n in neighbors:
            data = self.graph.nodes[n]
            nodes.append({
                "id": n,
                "label": data.get("label", n),
                "title": data.get("title", ""),
                "color": data.get("color", {}),
                "size": data.get("size", 15),
                "status": data.get("status", "unknown"),
            })
        
        edges = []
        for source, target in edges_to_include:
            edges.append({
                "from": source,
                "to": target,
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            })
        
        return {"nodes": nodes, "edges": edges}


# ─── Colores para clusters temáticos ───────────────────────────────────

CLUSTER_COLORS = [
    "#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
]


# ─── ThematicGraphBuilder ──────────────────────────────────────────────

class ThematicGraphBuilder:
    """
    Construye un grafo no-dirigido basado en similitud semántica.
    
    Nodos: Artículos incluidos.
    Aristas: Similitud coseno ≥ umbral (default 0.75).
    Clusters: Detectados con greedy_modularity_communities.
    
    Ejemplo:
        builder = ThematicGraphBuilder(threshold=0.75)
        embeddings, dois = await builder.get_or_generate_embeddings(articles)
        builder.set_embeddings(embeddings, dois)
        G = builder.build_undirected_graph()
        clusters = builder.detect_communities()
        builder.apply_cluster_colors(clusters)
        result = builder.serialize_and_save("project-id")
    """
    
    def __init__(self, threshold: float = 0.75):
        """
        Inicializa el builder temático.
        
        Args:
            threshold: Umbral mínimo de cosine_similarity para crear arista.
        """
        self.threshold = threshold
        self.graph: Optional[nx.Graph] = None
        self.embeddings: Optional[NDArray[np.float64]] = None
        self.article_dois: Optional[list[str]] = None
    
    def set_embeddings(
        self,
        embeddings: NDArray[np.float64],
        dois: list[str],
    ) -> None:
        """
        Establece embeddings y DOIs directamente (útil para testing).
        
        Args:
            embeddings: Matriz NxM de embeddings.
            dois: Lista de DOIs correspondientes.
        """
        self.embeddings = embeddings
        self.article_dois = dois
    
    async def get_or_generate_embeddings(
        self,
        articles: list[dict],
    ) -> tuple[NDArray[np.float64], list[str]]:
        """
        Obtiene o genera embeddings para los artículos.
        
        Usa nomic-embed-text vía Ollama.
        
        Args:
            articles: Lista de dicts con {doi, title, abstract}.
        
        Returns:
            (embeddings_matrix, dois_list)
        """
        dois = []
        texts = []
        
        for article in articles:
            doi = article.get("doi")
            if not doi:
                continue
            
            title = article.get("title", "")
            abstract = article.get("abstract", "")
            text = f"{title} {abstract}".strip()
            
            if text:
                dois.append(doi)
                texts.append(text)
        
        if not texts:
            empty = np.array([])
            self.set_embeddings(empty, [])
            return empty, []
        
        embeddings = await self._generate_embeddings_ollama(texts)
        self.set_embeddings(embeddings, dois)
        
        return embeddings, dois
    
    async def _generate_embeddings_ollama(self, texts: list[str]) -> NDArray[np.float64]:
        """
        Genera embeddings usando nomic-embed-text vía Ollama.
        
        POST http://localhost:11434/api/embeddings
        
        Args:
            texts: Lista de textos a embeddar.
        
        Returns:
            Matriz Nx768 de embeddings.
        """
        import aiohttp
        
        embeddings = []
        async with aiohttp.ClientSession() as session:
            for text in texts:
                payload = {
                    "model": "nomic-embed-text",
                    "prompt": text,
                }
                try:
                    async with session.post(
                        "http://localhost:11434/api/embeddings",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            embeddings.append(data["embedding"])
                        else:
                            embeddings.append([0.0] * 768)
                except Exception:
                    embeddings.append([0.0] * 768)
        
        return np.array(embeddings, dtype=np.float64)
    
    def compute_similarity_matrix(self) -> NDArray[np.float64]:
        """
        Calcula la matriz de similitud coseno.
        
        Returns:
            Matriz NxN de similitudes.
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            return np.array([], dtype=np.float64)
        
        return cosine_similarity(self.embeddings)
    
    def build_undirected_graph(self) -> nx.Graph:
        """
        Construye el grafo no-dirigido aplicando umbral de similitud.
        
        Returns:
            Grafo NetworkX Graph (no-dirigido).
        """
        if self.embeddings is None or len(self.article_dois) == 0:
            self.graph = nx.Graph()
            return self.graph
        
        similarity_matrix = self.compute_similarity_matrix()
        G = nx.Graph()
        
        # Añadir nodos
        for i, doi in enumerate(self.article_dois):
            G.add_node(
                doi,
                status="included",
                color={
                    "background": COLOR_INCLUDED,
                    "border": COLOR_BORDER_INCLUDED,
                },
                shape="dot",
                size=15,
            )
        
        # Añadir aristas donde similitud >= umbral
        n = len(self.article_dois)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(similarity_matrix[i][j])
                if sim >= self.threshold:
                    G.add_edge(
                        self.article_dois[i],
                        self.article_dois[j],
                        cosine_similarity=sim,
                        weight=sim,
                    )
        
        self.graph = G
        return G
    
    def detect_communities(self) -> dict[str, int]:
        """
        Detecta clusters temáticos usando greedy_modularity_communities.
        
        Returns:
            Dict {doi: cluster_id}
        """
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return {}
        
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = greedy_modularity_communities(self.graph)
        except Exception:
            return {node: 0 for node in self.graph.nodes()}
        
        cluster_map = {}
        for cluster_id, community in enumerate(communities):
            for node in community:
                cluster_map[node] = cluster_id
        
        return cluster_map
    
    def enrich_edges_with_keywords(
        self,
        articles_keywords: dict[str, list[str]],
    ) -> None:
        """
        Añade shared_keywords a cada arista.
        
        Args:
            articles_keywords: Dict {doi: [keywords]}
        """
        if self.graph is None:
            return
        
        for source, target in self.graph.edges():
            source_kws = set(articles_keywords.get(source, []))
            target_kws = set(articles_keywords.get(target, []))
            shared = source_kws & target_kws
            self.graph.edges[source, target]["shared_keywords"] = list(shared)
    
    def apply_cluster_colors(self, cluster_map: dict[str, int]) -> None:
        """
        Asigna colores a nodos según su cluster.
        
        Args:
            cluster_map: Dict {doi: cluster_id}
        """
        if self.graph is None:
            return
        
        for node, cluster_id in cluster_map.items():
            if node in self.graph:
                color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
                self.graph.nodes[node]["color"] = {
                    "background": color,
                    "border": color,
                }
                self.graph.nodes[node]["cluster"] = cluster_id
    
    def serialize_and_save(self, project_id: str, graph_dir: Optional[Path] = None, suffix: str = "included") -> dict:
        """
        Serializa el grafo temático a formato vis-network y guarda JSON.
        
        Args:
            project_id: UUID del proyecto.
            graph_dir: Directorio donde guardar. Default: data/projects/{id}/graphs/
            suffix: Suffix para el archivo (screening_status). Default: "included"
        
        Returns:
            Dict con {graph_type, project_id, nodes, edges, metadata}.
        """
        if self.graph is None:
            return {"nodes": [], "edges": [], "metadata": {}}
        
        G = self.graph
        nodes = []
        edges = []
        
        for node, data in G.nodes(data=True):
            nodes.append({
                "id": node,
                "label": data.get("label", node[:20] + "..."),
                "title": data.get("title", ""),
                "color": data.get("color", {}),
                "size": data.get("size", 15),
                "shape": data.get("shape", "dot"),
                "status": data.get("status", "included"),
                "cluster": data.get("cluster", 0),
            })
        
        for source, target, data in G.edges(data=True):
            sim = data.get("cosine_similarity", 0)
            width = 1 + sim * 4
            edges.append({
                "from": source,
                "to": target,
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": width,
                "dashes": [5, 5],
                "cosine_similarity": round(sim, 3),
                "shared_keywords": data.get("shared_keywords", []),
            })
        
        cluster_counts = {}
        for node in G.nodes():
            cluster = G.nodes[node].get("cluster", 0)
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        
        result = {
            "graph_type": "thematic",
            "project_id": project_id,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "threshold": self.threshold,
                "num_clusters": len(cluster_counts),
                "cluster_sizes": cluster_counts,
                "screening_status": suffix,
            },
        }
        
        # Guardar a disco si graph_dir está disponible
        if graph_dir is None:
            graph_dir = Path(f"data/projects/{project_id}/graphs")
        
        graph_dir.mkdir(parents=True, exist_ok=True)
        output_path = graph_dir / f"thematic_graph_{suffix}.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        
        return result
