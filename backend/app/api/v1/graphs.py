"""
Archivo: graphs.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Endpoints REST para exploración de grafos bibliográficos.

Expone 5 endpoints para construir, consultar y explorar grafos de citación
y temáticos. Los grafos se almacenan como JSON en disco por proyecto.

Acciones Principales:
    - POST /{project_id}/build: Construir ambos grafos (citación + temático).
    - GET /{project_id}/citation: Obtener grafo de citaciones con filtros.
    - GET /{project_id}/thematic: Obtener grafo temático con umbral configurable.
    - GET /{project_id}/article/{doi}/neighbors: Obtener vecinos de un artículo.
    - GET /{project_id}/stats: Obtener estadísticas de ambos grafos.

Entradas / Dependencias:
    - `CitationGraphBuilder`: Construcción y carga de grafo de citaciones.
    - `ThematicGraphBuilder`: Construcción de grafo temático.
    - `build_reference_batch`: Extracción de referencias.
    - JSON en disco: data/projects/{project_id}/graphs/*.json

Salidas / Efectos:
    - Respuestas JSON validadas con Pydantic.
    - Grafos serializados en disco.

Ejemplo de Integración:
    # Construir grafos:
    POST /api/v1/graphs/{project_id}/build
    
    # Obtener grafo de citaciones:
    GET /api/v1/graphs/{project_id}/citation?status=included&depth=1
    
    # Obtener grafo temático:
    GET /api/v1/graphs/{project_id}/thematic?threshold=0.75
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.graph_models import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphResponse,
    GraphStatsResponse,
    NeighborResponse,
)
from app.services.graph_service import CitationGraphBuilder, ThematicGraphBuilder
from app.services.reference_extractor import build_reference_batch

router = APIRouter(prefix="/graphs", tags=["graphs"])

GRAPH_DIR = Path("data/projects")


@router.post("/{project_id}/build")
async def build_graphs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara la construcción de ambos grafos (citación + temático).
    
    Flujo:
    1. Extraer referencias de artículos del proyecto.
    2. Construir grafo de citaciones (dirigido).
    3. Construir grafo temático (no-dirigido).
    4. Guardar ambos grafos como JSON en disco.
    
    Retorna estadísticas del proceso completo.
    
    Args:
        project_id: UUID del proyecto.
        db: Sesión de base de datos (inyectada por FastAPI).
    
    Returns:
        Dict con estadísticas de extracción, citación y temático.
    """
    try:
        # Paso 1: Extraer referencias
        ref_stats = await build_reference_batch(project_id, db)
        
        # Paso 2: Construir grafo de citaciones
        citation_builder = CitationGraphBuilder(db, project_id)
        await citation_builder.build_directed_graph()
        citation_path = citation_builder.save_graph()
        citation_metrics = citation_builder.calculate_metrics()
        
        # Paso 3: Construir grafo temático
        thematic_builder = ThematicGraphBuilder()
        thematic_dir = GRAPH_DIR / project_id / "graphs"
        thematic_data = thematic_builder.serialize_and_save(project_id, thematic_dir)
        
        return {
            "status": "complete",
            "reference_extraction": ref_stats,
            "citation_graph": citation_metrics,
            "thematic_graph": thematic_data.get("metadata", {}),
            "citation_path": str(citation_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/citation", response_model=GraphResponse)
async def get_citation_graph(
    project_id: str,
    year_min: Optional[int] = Query(None, description="Año mínimo de filtrado"),
    year_max: Optional[int] = Query(None, description="Año máximo de filtrado"),
    status: Optional[str] = Query(None, description="Filtrar por status: included | cited_external"),
    depth: int = Query(1, ge=1, le=3, description="Profundidad de expansión"),
):
    """
    Retorna el grafo de citaciones completo.
    
    Filtros opcionales:
    - year_min/year_max: rango de años de los artículos.
    - status: "included" para artículos del proyecto, "cited_external" para externos.
    - depth: profundidad de expansión del grafo.
    
    Args:
        project_id: UUID del proyecto.
        year_min: Año mínimo.
        year_max: Año máximo.
        status: Status del nodo.
        depth: Profundidad.
    
    Returns:
        GraphResponse con nodos, aristas y metadata.
    
    Raises:
        404: Si el grafo no ha sido construido.
    """
    graph_data = CitationGraphBuilder.load_graph(project_id)
    if graph_data is None:
        raise HTTPException(
            status_code=404,
            detail="Grafo no construido. Ejecuta POST /graphs/{project_id}/build primero.",
        )
    
    # Aplicar filtros
    filtered_nodes = graph_data["nodes"]
    
    if status:
        filtered_nodes = [n for n in filtered_nodes if n.get("status") == status]
    
    if year_min is not None or year_max is not None:
        filtered_nodes_year = []
        for n in filtered_nodes:
            node_year = n.get("title", "")
            # Intentar extraer año del título o metadata
            year_str = ""
            for part in node_year.split():
                if part.isdigit() and len(part) == 4:
                    year_str = part
            if year_str:
                year = int(year_str)
                if year_min and year < year_min:
                    continue
                if year_max and year > year_max:
                    continue
            filtered_nodes_year.append(n)
        filtered_nodes = filtered_nodes_year
    
    filtered_node_ids = {n["id"] for n in filtered_nodes}
    filtered_edges = [
        e for e in graph_data["edges"]
        if e.get("from") in filtered_node_ids and e.get("to") in filtered_node_ids
    ]
    
    metadata = graph_data.get("metadata", {})
    
    return GraphResponse(
        graph_type="citation",
        project_id=project_id,
        nodes=[GraphNode(**n) for n in filtered_nodes],
        edges=[GraphEdge(**e) for e in filtered_edges],
        metadata=GraphMetadata(**metadata) if metadata else GraphMetadata(),
    )


@router.get("/{project_id}/thematic", response_model=GraphResponse)
async def get_thematic_graph(
    project_id: str,
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="Umbral mínimo de cosine_similarity"),
):
    """
    Retorna el grafo temático con umbral configurable.
    
    El umbral controla qué aristas se incluyen según su similitud coseno.
    Umbral más alto = menos aristas (solo más similares).
    Umbral más bajo = más aristas (incluye menos similares).
    
    Args:
        project_id: UUID del proyecto.
        threshold: Umbral de similitud (0.0 a 1.0).
    
    Returns:
        GraphResponse con nodos, aristas filtradas y metadata.
    
    Raises:
        404: Si el grafo temático no ha sido construido.
    """
    thematic_path = GRAPH_DIR / project_id / "graphs" / "thematic_graph.json"
    if not thematic_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Grafo temático no construido. Ejecuta POST /graphs/{project_id}/build primero.",
        )
    
    data = json.loads(thematic_path.read_text(encoding="utf-8"))
    
    # Filtrar aristas por umbral
    filtered_edges = [
        e for e in data["edges"]
        if e.get("cosine_similarity", 0) >= threshold
    ]
    
    metadata = data.get("metadata", {})
    metadata["threshold"] = threshold
    
    return GraphResponse(
        graph_type="thematic",
        project_id=project_id,
        nodes=[GraphNode(**n) for n in data["nodes"]],
        edges=[GraphEdge(**e) for e in filtered_edges],
        metadata=GraphMetadata(**metadata) if metadata else GraphMetadata(),
    )


@router.get("/{project_id}/article/{doi:path}/neighbors", response_model=NeighborResponse)
async def get_article_neighbors(
    project_id: str,
    doi: str,
    depth: int = Query(1, ge=1, le=3, description="Profundidad de expansión"),
):
    """
    Retorna los vecinos de un artículo específico en el grafo de citaciones.
    
    Vecinos incluyen:
    - Artículos que citan a este artículo (predecesores).
    - Artículos citados por este artículo (sucesores).
    
    Args:
        project_id: UUID del proyecto.
        doi: DOI del artículo (con path encoding).
        depth: Profundidad de expansión (1-3).
    
    Returns:
        NeighborResponse con nodos vecinos y aristas conectadas.
    
    Raises:
        404: Si el grafo no existe o el DOI no se encuentra.
    """
    graph_data = CitationGraphBuilder.load_graph(project_id)
    if graph_data is None:
        raise HTTPException(status_code=404, detail="Grafo no construido.")
    
    # Verificar que el DOI existe en el grafo
    node_ids = {n["id"] for n in graph_data["nodes"]}
    if doi not in node_ids:
        raise HTTPException(status_code=404, detail=f"DOI {doi} no encontrado en el grafo.")
    
    # Reconstruir grafo para usar get_neighbors
    import networkx as nx
    G = nx.DiGraph()
    
    for node in graph_data["nodes"]:
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
    
    for edge in graph_data["edges"]:
        G.add_edge(edge["from"], edge["to"])
    
    # Obtener vecinos
    neighbors = set()
    edges_to_include = []
    
    if depth == 1:
        for neighbor in G.predecessors(doi):
            neighbors.add(neighbor)
            edges_to_include.append((neighbor, doi))
        for neighbor in G.successors(doi):
            neighbors.add(neighbor)
            edges_to_include.append((doi, neighbor))
    else:
        visited = {doi}
        current_level = {doi}
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in G.predecessors(node):
                    if neighbor not in visited:
                        next_level.add(neighbor)
                        edges_to_include.append((neighbor, node))
                for neighbor in G.successors(node):
                    if neighbor not in visited:
                        next_level.add(neighbor)
                        edges_to_include.append((node, neighbor))
            visited.update(next_level)
            neighbors.update(next_level)
            current_level = next_level
    
    # Construir respuesta
    node_map = {n["id"]: n for n in graph_data["nodes"]}
    result_nodes = []
    for n_id in neighbors:
        if n_id in node_map:
            result_nodes.append(GraphNode(**node_map[n_id]))
    
    edge_map = {(e["from"], e["to"]): e for e in graph_data["edges"]}
    result_edges = []
    for src, tgt in edges_to_include:
        key = (src, tgt)
        if key in edge_map:
            result_edges.append(GraphEdge(**edge_map[key]))
    
    return NeighborResponse(nodes=result_nodes, edges=result_edges)


@router.get("/{project_id}/stats", response_model=GraphStatsResponse)
async def get_graph_stats(project_id: str):
    """
    Retorna estadísticas de ambos grafos para un proyecto.
    
    Incluye:
    - Metadata del grafo de citaciones.
    - Metadata del grafo temático.
    - Estado de construcción (ready, partial, not_built).
    
    Args:
        project_id: UUID del proyecto.
    
    Returns:
        GraphStatsResponse con estadísticas completas.
    """
    citation_path = GRAPH_DIR / project_id / "graphs" / "citation_graph.json"
    thematic_path = GRAPH_DIR / project_id / "graphs" / "thematic_graph.json"
    
    citation_data = None
    thematic_data = None
    
    if citation_path.exists():
        citation_data = json.loads(citation_path.read_text(encoding="utf-8"))
    if thematic_path.exists():
        thematic_data = json.loads(thematic_path.read_text(encoding="utf-8"))
    
    build_status = "not_built"
    if citation_data and thematic_data:
        build_status = "ready"
    elif citation_data or thematic_data:
        build_status = "partial"
    
    return GraphStatsResponse(
        project_id=project_id,
        citation_graph=citation_data.get("metadata", {}) if citation_data else {},
        thematic_graph=thematic_data.get("metadata", {}) if thematic_data else {},
        total_included_articles=0,
        total_references=0,
        build_status=build_status,
    )
