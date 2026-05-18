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
    {"screening_status": "included"}
    
    # Obtener grafo de citaciones:
    GET /api/v1/graphs/{project_id}/citation?screening_status=included&depth=1
    
    # Obtener grafo temático:
    GET /api/v1/graphs/{project_id}/thematic?threshold=0.75&screening_status=included
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, async_session_factory
from app.models.graph_models import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphResponse,
    GraphStatsResponse,
    NeighborResponse,
)
from app.services.graph_service import (
    CitationGraphBuilder,
    ThematicGraphBuilder,
    get_eligible_articles_for_graphs,
    has_screening_decisions,
)
from app.services.reference_extractor import build_reference_batch_from_md
from app.api.v1.events import publish_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graphs", tags=["graphs"])

GRAPH_DIR = Path("data/projects")

# ─── In-memory build status tracker ────────────────────────────────────
_build_statuses: dict[str, dict] = {}


def get_build_status(project_id: str) -> Optional[dict]:
    """Get current build status for a project."""
    return _build_statuses.get(project_id)


def set_build_status(project_id: str, status: dict):
    """Update build status for a project."""
    _build_statuses[project_id] = status

router = APIRouter(prefix="/graphs", tags=["graphs"])

GRAPH_DIR = Path("data/projects")


class BuildGraphRequest(BaseModel):
    screening_status: str = "included"


async def _build_graphs_background(
    project_id: str,
    screening_status: str,
):
    """
    Background task that builds both graphs and publishes SSE progress events.
    
    Flujo:
    1. Extract references from local .md files
    2. Build citation graph
    3. Build thematic graph
    4. Publish success/error event
    """
    from app.db.database import async_session_factory
    
    build_id = str(uuid.uuid4())[:8]
    set_build_status(project_id, {
        "build_id": build_id,
        "status": "running",
        "progress": 0,
        "step": "initializing",
        "screening_status": screening_status,
    })
    
    await publish_event(project_id, {
        "type": "graph_build_progress",
        "build_id": build_id,
        "progress": 0,
        "step": "initializing",
        "message": "Iniciando construcción del grafo...",
    })
    
    try:
        async with async_session_factory() as db:
            # Step 1: Extract references from MD (25%)
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 10,
                "step": "extracting_references",
                "message": "Extrayendo referencias desde archivos Markdown...",
            })
            
            ref_stats = await build_reference_batch_from_md(project_id, db, screening_status)
            
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 25,
                "step": "references_complete",
                "message": f"Referencias extraídas: {ref_stats['total_references_extracted']}",
                "details": ref_stats,
            })
            
            # Step 2: Build citation graph (50%)
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 30,
                "step": "building_citation_graph",
                "message": "Construyendo grafo de citaciones...",
            })
            
            citation_builder = CitationGraphBuilder(db, project_id)
            await citation_builder.build_directed_graph(screening_status)
            citation_path = citation_builder.save_graph(suffix=screening_status)
            citation_metrics = citation_builder.calculate_metrics()
            
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 50,
                "step": "citation_graph_complete",
                "message": f"Grafo de citaciones: {citation_metrics.get('nodes', 0)} nodos, {citation_metrics.get('edges', 0)} aristas",
                "details": citation_metrics,
            })
            
            # Step 3: Build thematic graph (75%)
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 55,
                "step": "building_thematic_graph",
                "message": "Construyendo grafo temático...",
            })
            
            thematic_builder = ThematicGraphBuilder()
            thematic_dir = GRAPH_DIR / project_id / "graphs"
            
            eligible_articles = await get_eligible_articles_for_graphs(
                project_id, db, screening_status
            )
            
            articles_for_embeddings = [
                {
                    "doi": a.doi,
                    "title": a.title or "",
                    "abstract": a.abstract or "",
                }
                for a in eligible_articles
            ]
            
            if articles_for_embeddings:
                embeddings, dois = await thematic_builder.get_or_generate_embeddings(
                    articles_for_embeddings
                )
                if len(dois) > 0:
                    thematic_builder.build_undirected_graph()
                    thematic_builder.detect_communities()
                    thematic_builder.apply_cluster_colors(thematic_builder.detect_communities())
            
            thematic_data = thematic_builder.serialize_and_save(
                project_id, thematic_dir, suffix=screening_status
            )
            
            await publish_event(project_id, {
                "type": "graph_build_progress",
                "build_id": build_id,
                "progress": 75,
                "step": "thematic_graph_complete",
                "message": f"Grafo temático: {thematic_data.get('metadata', {}).get('nodes', 0)} nodos",
                "details": thematic_data.get("metadata", {}),
            })
            
            # Step 4: Complete (100%)
            await publish_event(project_id, {
                "type": "graph_build_success",
                "build_id": build_id,
                "progress": 100,
                "step": "complete",
                "message": "Construcción completada exitosamente",
                "results": {
                    "screening_status": screening_status,
                    "reference_extraction": ref_stats,
                    "citation_graph": citation_metrics,
                    "thematic_graph": thematic_data.get("metadata", {}),
                    "citation_path": str(citation_path),
                },
            })
            
            set_build_status(project_id, {
                "build_id": build_id,
                "status": "completed",
                "progress": 100,
                "step": "complete",
                "screening_status": screening_status,
                "results": {
                    "reference_extraction": ref_stats,
                    "citation_graph": citation_metrics,
                    "thematic_graph": thematic_data.get("metadata", {}),
                },
            })
            
    except Exception as e:
        logger.exception(f"Graph build failed for project {project_id}")
        
        await publish_event(project_id, {
            "type": "graph_build_error",
            "build_id": build_id,
            "progress": -1,
            "step": "error",
            "message": f"Error durante la construcción: {str(e)}",
            "error": str(e),
        })
        
        set_build_status(project_id, {
            "build_id": build_id,
            "status": "failed",
            "progress": -1,
            "step": "error",
            "screening_status": screening_status,
            "error": str(e),
        })


@router.post("/{project_id}/build", status_code=202)
async def build_graphs(
    project_id: str,
    background_tasks: BackgroundTasks,
    request: BuildGraphRequest = BuildGraphRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara la construcción asíncrona de ambos grafos (citación + temático).
    
    Flujo:
    1. Valida screening_status.
    2. Inicia BackgroundTask que extrae referencias y construye grafos.
    3. Retorna 202 Accepted inmediatamente con build_id.
    4. El frontend subscribe a SSE /events/{project_id} para progreso.
    
    Args:
        project_id: UUID del proyecto.
        background_tasks: FastAPI BackgroundTasks.
        request: Body con screening_status (included/maybe/all).
        db: Sesión de base de datos (inyectada por FastAPI).
    
    Returns:
        202 Accepted con build_id y status endpoint.
    """
    screening_status = request.screening_status
    if screening_status not in ("included", "maybe", "all"):
        raise HTTPException(
            status_code=400,
            detail="screening_status debe ser 'included', 'maybe' o 'all'."
        )
    
    # Auto-fallback a "all" si no hay decisiones de screening
    applied_fallback = False
    if screening_status != "all":
        has_decisions = await has_screening_decisions(project_id, db)
        if not has_decisions:
            logger.info(
                f"No screening decisions for project {project_id}, "
                f"falling back to screening_status='all'"
            )
            screening_status = "all"
            applied_fallback = True
    
    build_id = str(uuid.uuid4())[:8]
    
    background_tasks.add_task(
        _build_graphs_background,
        project_id,
        screening_status,
    )
    
    return {
        "status": "accepted",
        "build_id": build_id,
        "message": "Construcción de grafos iniciada en segundo plano",
        "screening_status": screening_status,
        "applied_fallback": applied_fallback,
        "progress_endpoint": f"/api/v1/events/{project_id}",
        "status_endpoint": f"/api/v1/graphs/{project_id}/build/{build_id}/status",
    }


@router.get("/{project_id}/build/{build_id}/status")
async def get_build_status_endpoint(project_id: str, build_id: str):
    """
    Consulta el estado actual de una construcción de grafo.
    
    Args:
        project_id: UUID del proyecto.
        build_id: ID de la construcción.
    
    Returns:
        Estado actual del build (running, completed, failed).
    """
    status = get_build_status(project_id)
    if status is None:
        raise HTTPException(status_code=404, detail="No hay construcción activa para este proyecto.")
    
    if status.get("build_id") != build_id:
        return {
            "status": "mismatch",
            "message": "El build_id no coincide con la construcción actual",
            "current_build_id": status.get("build_id"),
        }
    
    return status


@router.get("/{project_id}/citation", response_model=GraphResponse)
async def get_citation_graph(
    project_id: str,
    screening_status: str = Query("included", description="Filtrar por screening: included | maybe | all"),
    year_min: Optional[int] = Query(None, description="Año mínimo de filtrado"),
    year_max: Optional[int] = Query(None, description="Año máximo de filtrado"),
    status: Optional[str] = Query(None, description="Filtrar por status: included | cited_external"),
    depth: int = Query(1, ge=1, le=3, description="Profundidad de expansión"),
):
    """
    Retorna el grafo de citaciones completo.
    
    Filtros opcionales:
    - screening_status: "included" (default), "maybe", o "all".
    - year_min/year_max: rango de años de los artículos.
    - status: "included" para artículos del proyecto, "cited_external" para externos.
    - depth: profundidad de expansión del grafo.
    
    Args:
        project_id: UUID del proyecto.
        screening_status: Screening status del grafo.
        year_min: Año mínimo.
        year_max: Año máximo.
        status: Status del nodo.
        depth: Profundidad.
    
    Returns:
        GraphResponse con nodos, aristas y metadata.
    
    Raises:
        404: Si el grafo no ha sido construido.
    """
    if screening_status not in ("included", "maybe", "all"):
        raise HTTPException(
            status_code=400,
            detail="screening_status debe ser 'included', 'maybe' o 'all'."
        )
    
    graph_data = CitationGraphBuilder.load_graph(project_id, suffix=screening_status)
    if graph_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Grafo no construido para screening_status='{screening_status}'. Ejecuta POST /graphs/{{project_id}}/build primero.",
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
    screening_status: str = Query("included", description="Filtrar por screening: included | maybe | all"),
    threshold: float = Query(0.75, ge=0.0, le=1.0, description="Umbral mínimo de cosine_similarity"),
):
    """
    Retorna el grafo temático con umbral configurable.
    
    El umbral controla qué aristas se incluyen según su similitud coseno.
    Umbral más alto = menos aristas (solo más similares).
    Umbral más bajo = más aristas (incluye menos similares).
    
    Args:
        project_id: UUID del proyecto.
        screening_status: Screening status del grafo.
        threshold: Umbral de similitud (0.0 a 1.0).
    
    Returns:
        GraphResponse con nodos, aristas filtradas y metadata.
    
    Raises:
        404: Si el grafo temático no ha sido construido.
    """
    if screening_status not in ("included", "maybe", "all"):
        raise HTTPException(
            status_code=400,
            detail="screening_status debe ser 'included', 'maybe' o 'all'."
        )
    
    thematic_path = GRAPH_DIR / project_id / "graphs" / f"thematic_graph_{screening_status}.json"
    if not thematic_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Grafo temático no construido para screening_status='{screening_status}'. Ejecuta POST /graphs/{{project_id}}/build primero.",
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
    screening_status: str = Query("included", description="Filtrar por screening: included | maybe | all"),
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
        screening_status: Screening status del grafo.
        depth: Profundidad de expansión (1-3).
    
    Returns:
        NeighborResponse con nodos vecinos y aristas conectadas.
    
    Raises:
        404: Si el grafo no existe o el DOI no se encuentra.
    """
    if screening_status not in ("included", "maybe", "all"):
        raise HTTPException(
            status_code=400,
            detail="screening_status debe ser 'included', 'maybe' o 'all'."
        )
    
    graph_data = CitationGraphBuilder.load_graph(project_id, suffix=screening_status)
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
async def get_graph_stats(
    project_id: str,
    screening_status: str = Query("included", description="Filtrar por screening: included | maybe | all"),
):
    """
    Retorna estadísticas de ambos grafos para un proyecto.
    
    Incluye:
    - Metadata del grafo de citaciones.
    - Metadata del grafo temático.
    - Estado de construcción (ready, partial, not_built).
    
    Args:
        project_id: UUID del proyecto.
        screening_status: Screening status del grafo.
    
    Returns:
        GraphStatsResponse con estadísticas completas.
    """
    if screening_status not in ("included", "maybe", "all"):
        raise HTTPException(
            status_code=400,
            detail="screening_status debe ser 'included', 'maybe' o 'all'."
        )
    
    citation_path = GRAPH_DIR / project_id / "graphs" / f"citation_graph_{screening_status}.json"
    thematic_path = GRAPH_DIR / project_id / "graphs" / f"thematic_graph_{screening_status}.json"
    
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
