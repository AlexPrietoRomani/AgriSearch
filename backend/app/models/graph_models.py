"""
Archivo: graph_models.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Modelos Pydantic para validar las respuestas JSON de la API de grafos.

Define schemas tipados para nodos, aristas, metadata y respuestas completas
de los endpoints de grafos de citación y temáticos.

Acciones Principales:
    - Validar estructura de nodos del grafo (GraphNode).
    - Validar estructura de aristas con soporte para alias `from` (GraphEdge).
    - Validar metadata de grafos con métricas (GraphMetadata).
    - Validar respuestas completas de grafos (GraphResponse).
    - Validar respuestas de estadísticas (GraphStatsResponse).
    - Validar respuestas de vecinos (NeighborResponse).

Entradas / Dependencias:
    - `pydantic` v2: Validación de schemas.

Salidas / Efectos:
    - Modelos Pydantic listos para usar como response_model en FastAPI.

Ejemplo de Integración:
    from app.models.graph_models import GraphResponse, GraphEdge
    
    @router.get("/citation", response_model=GraphResponse)
    async def get_citation_graph(project_id: str):
        ...
"""

from typing import Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Representa un nodo en el grafo (artículo)."""
    id: str
    label: str
    title: str = ""
    color: dict = Field(default_factory=dict)
    size: float = 15
    shape: str = "dot"
    status: str = "unknown"
    cluster: Optional[int] = None


class GraphEdge(BaseModel):
    """Representa una arista en el grafo (relación de citación o similitud)."""
    from_node: str = Field(alias="from")
    to: str
    arrows: Optional[str] = None
    color: dict = Field(default_factory=dict)
    width: float = 1.5
    dashes: Optional[list[int]] = None
    cosine_similarity: Optional[float] = None
    shared_keywords: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class GraphMetadata(BaseModel):
    """Metadata del grafo con métricas calculadas."""
    total_nodes: int = 0
    total_edges: int = 0
    total_included: int = 0
    total_external: int = 0
    most_cited: list[dict] = Field(default_factory=list)
    bridge_articles: list[dict] = Field(default_factory=list)
    density: float = 0.0
    threshold: Optional[float] = None
    num_clusters: Optional[int] = None
    cluster_sizes: Optional[dict] = None


class GraphResponse(BaseModel):
    """Respuesta completa de un grafo (citación o temático)."""
    graph_type: str  # "citation" | "thematic"
    project_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metadata: GraphMetadata


class GraphStatsResponse(BaseModel):
    """Respuesta de estadísticas de ambos grafos."""
    project_id: str
    citation_graph: dict
    thematic_graph: dict
    total_included_articles: int
    total_references: int
    build_status: str  # "ready" | "not_built" | "partial"


class NeighborResponse(BaseModel):
    """Respuesta de vecinos de un artículo."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
