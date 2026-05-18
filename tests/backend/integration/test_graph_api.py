"""
Archivo: test_graph_api.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Tests de integración para los endpoints REST de grafos.

Valida que los endpoints retornan respuestas correctas con datos mock,
incluyendo filtros, 404s cuando el grafo no existe, y formato de respuesta.

Acciones Principales:
    - Testear endpoint de citación con datos mock.
    - Testear endpoint temático con filtrado por umbral.
    - Testear endpoint de estadísticas.
    - Testear endpoint de vecinos.
    - Testear 404 cuando grafo no existe.
    - Testear formato de respuesta Pydantic.

Ejemplo de Ejecución:
    pytest tests/backend/integration/test_graph_api.py -v
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
import app.api.v1.graphs as graphs_module


@pytest.fixture
def client():
    """Crea un cliente de test para FastAPI."""
    return TestClient(app)


@pytest.fixture
def graph_data_dir(tmp_path, monkeypatch):
    """Crea un directorio de grafos mock en tmp_path y parchea todas las rutas."""
    project_id = "test-project-001"
    graph_dir = tmp_path / "projects" / project_id / "graphs"
    graph_dir.mkdir(parents=True)

    # Parchear GRAPH_DIR en el módulo graphs
    monkeypatch.setattr(graphs_module, "GRAPH_DIR", tmp_path / "projects")

    # Parchear CitationGraphBuilder.load_graph
    @staticmethod
    def patched_load(project_id, graph_dir_param=None):
        if graph_dir_param is None:
            graph_dir_param = tmp_path / "projects" / project_id / "graphs"
        json_path = graph_dir_param / "citation_graph.json"
        if not json_path.exists():
            return None
        return json.loads(json_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(graphs_module.CitationGraphBuilder, "load_graph", patched_load)

    # Parchear Path.exists y Path.read_text para stats y thematic endpoints
    original_path_init = Path.__init__

    def patched_graph_path(self, *args, **kwargs):
        # No intercept Path construction, just let it be
        pass

    return graph_dir, project_id


@pytest.fixture
def mock_citation_graph(graph_data_dir):
    """Crea un grafo de citación mock en disco."""
    graph_dir, project_id = graph_data_dir

    data = {
        "graph_type": "citation",
        "project_id": project_id,
        "nodes": [
            {
                "id": "10.1111/a",
                "label": "Smith (2020)",
                "title": "Paper A about crop yield",
                "color": {"background": "#22c55e", "border": "#16a34a"},
                "size": 20,
                "shape": "dot",
                "status": "included",
            },
            {
                "id": "10.2222/b",
                "label": "Jones (2021)",
                "title": "Paper B about soil analysis",
                "color": {"background": "#22c55e", "border": "#16a34a"},
                "size": 18,
                "shape": "dot",
                "status": "included",
            },
            {
                "id": "10.3333/ext1",
                "label": "Brown (2019)",
                "title": "External Paper about ML",
                "color": {"background": "#3b82f6", "border": "#2563eb"},
                "size": 12,
                "shape": "dot",
                "status": "cited_external",
            },
        ],
        "edges": [
            {
                "from": "10.1111/a",
                "to": "10.3333/ext1",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
            {
                "from": "10.2222/b",
                "to": "10.3333/ext1",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
        ],
        "metadata": {
            "total_nodes": 3,
            "total_edges": 2,
            "total_included": 2,
            "total_external": 1,
            "most_cited": [{"doi": "10.3333/ext1", "in_degree": 2}],
            "bridge_articles": [{"doi": "10.3333/ext1", "cited_by_count": 2}],
            "density": 0.33,
        },
    }

    (graph_dir / "citation_graph.json").write_text(json.dumps(data), encoding="utf-8")
    return graph_dir, project_id, data


@pytest.fixture
def mock_thematic_graph(graph_data_dir):
    """Crea un grafo temático mock en disco."""
    graph_dir, project_id = graph_data_dir

    data = {
        "graph_type": "thematic",
        "project_id": project_id,
        "nodes": [
            {
                "id": "10.1111/a",
                "label": "A",
                "title": "Paper A",
                "color": {"background": "#22c55e"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 0,
            },
            {
                "id": "10.2222/b",
                "label": "B",
                "title": "Paper B",
                "color": {"background": "#3b82f6"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 1,
            },
            {
                "id": "10.4444/c",
                "label": "C",
                "title": "Paper C",
                "color": {"background": "#22c55e"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 0,
            },
        ],
        "edges": [
            {
                "from": "10.1111/a",
                "to": "10.2222/b",
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": 3.2,
                "dashes": [5, 5],
                "cosine_similarity": 0.85,
                "shared_keywords": ["ml", "agriculture"],
            },
            {
                "from": "10.1111/a",
                "to": "10.4444/c",
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": 2.0,
                "dashes": [5, 5],
                "cosine_similarity": 0.55,
                "shared_keywords": ["agriculture"],
            },
        ],
        "metadata": {
            "total_nodes": 3,
            "total_edges": 2,
            "threshold": 0.75,
            "num_clusters": 2,
            "cluster_sizes": {"0": 2, "1": 1},
        },
    }

    (graph_dir / "thematic_graph.json").write_text(json.dumps(data), encoding="utf-8")
    return graph_dir, project_id, data


# ──────────────────────────────────────────────
# Tests de endpoint de citación
# ──────────────────────────────────────────────

class TestCitationGraphEndpoint:
    """Tests del endpoint GET /graphs/{project_id}/citation."""

    def test_citation_endpoint_response_format(self, client, mock_citation_graph):
        """El endpoint de citación retorna formato correcto."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/citation")
        assert response.status_code == 200

        data = response.json()
        assert data["graph_type"] == "citation"
        assert data["project_id"] == project_id
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert "metadata" in data

    def test_citation_endpoint_filter_by_status(self, client, mock_citation_graph):
        """Filtrar por status retorna solo nodos del status solicitado."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/citation?status=included")
        assert response.status_code == 200

        data = response.json()
        assert all(n["status"] == "included" for n in data["nodes"])
        assert len(data["nodes"]) == 2

    def test_citation_endpoint_filter_external(self, client, mock_citation_graph):
        """Filtrar por cited_external retorna solo nodos externos."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/citation?status=cited_external")
        assert response.status_code == 200

        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["status"] == "cited_external"

    def test_404_when_graph_does_not_exist(self, client):
        """Retorna 404 cuando el grafo no existe."""
        response = client.get("/api/v1/graphs/nonexistent-project/citation")
        assert response.status_code == 404
        assert "no construido" in response.json()["detail"].lower()

    def test_citation_metadata_contains_counts(self, client, mock_citation_graph):
        """Metadata contiene contadores correctos."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/citation")
        data = response.json()

        meta = data["metadata"]
        assert meta["total_nodes"] == 3
        assert meta["total_edges"] == 2
        assert meta["total_included"] == 2
        assert meta["total_external"] == 1


# ──────────────────────────────────────────────
# Tests de endpoint temático
# ──────────────────────────────────────────────

class TestThematicGraphEndpoint:
    """Tests del endpoint GET /graphs/{project_id}/thematic."""

    def test_thematic_endpoint_response_format(self, client, mock_thematic_graph):
        """El endpoint temático retorna formato correcto."""
        _, project_id, _ = mock_thematic_graph

        # threshold=0.5 para incluir ambas aristas (0.85 y 0.55)
        response = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.5")
        assert response.status_code == 200

        data = response.json()
        assert data["graph_type"] == "thematic"
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2

    def test_thematic_endpoint_with_threshold(self, client, mock_thematic_graph):
        """El endpoint temático filtra por umbral."""
        _, project_id, _ = mock_thematic_graph

        # threshold=0.75: ambas aristas (0.85 y 0.55) → solo 0.85 >= 0.75
        response = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.75")
        assert response.status_code == 200
        data = response.json()
        assert len(data["edges"]) == 1  # Solo 0.85 >= 0.75

        # threshold=0.5: ambas aristas >= 0.5
        response = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["edges"]) == 2

        # threshold=0.9: ninguna arista >= 0.9
        response = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.9")
        assert response.status_code == 200
        data = response.json()
        assert len(data["edges"]) == 0

    def test_thematic_404_when_not_built(self, client):
        """Retorna 404 cuando el grafo temático no existe."""
        response = client.get("/api/v1/graphs/nonexistent-project/thematic")
        assert response.status_code == 404

    def test_thematic_edges_have_dashes(self, client, mock_thematic_graph):
        """Aristas temáticas tienen dashes [5, 5]."""
        _, project_id, _ = mock_thematic_graph

        response = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.5")
        data = response.json()

        for edge in data["edges"]:
            assert edge["dashes"] == [5, 5]
            assert "cosine_similarity" in edge


# ──────────────────────────────────────────────
# Tests de endpoint de estadísticas
# ──────────────────────────────────────────────

class TestGraphStatsEndpoint:
    """Tests del endpoint GET /graphs/{project_id}/stats."""

    def test_stats_endpoint_returns_counts(self, client, mock_citation_graph):
        """El endpoint de stats retorna contadores."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["project_id"] == project_id
        assert data["build_status"] in ["ready", "partial", "not_built"]
        assert "citation_graph" in data
        assert "thematic_graph" in data

    def test_stats_build_status_ready(self, client, mock_citation_graph, mock_thematic_graph):
        """build_status = 'ready' cuando ambos grafos existen."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/stats")
        data = response.json()
        assert data["build_status"] == "ready"

    def test_stats_build_status_partial(self, client, mock_citation_graph):
        """build_status = 'partial' cuando solo existe un grafo."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/stats")
        data = response.json()
        assert data["build_status"] == "partial"

    def test_stats_build_status_not_built(self, client):
        """build_status = 'not_built' cuando no existe ningún grafo."""
        response = client.get("/api/v1/graphs/nonexistent-project/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["build_status"] == "not_built"
        assert data["citation_graph"] == {}
        assert data["thematic_graph"] == {}


# ──────────────────────────────────────────────
# Tests de endpoint de vecinos
# ──────────────────────────────────────────────

class TestArticleNeighborsEndpoint:
    """Tests del endpoint GET /graphs/{project_id}/article/{doi}/neighbors."""

    def test_neighbors_endpoint_returns_adjacent_nodes(self, client, mock_citation_graph):
        """El endpoint de vecinos retorna nodos conectados."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/article/10.3333%2Fext1/neighbors")
        assert response.status_code == 200

        data = response.json()
        assert len(data["nodes"]) == 2  # 10.1111/a y 10.2222/b citan a ext1
        assert len(data["edges"]) == 2

    def test_neighbors_404_graph_not_built(self, client):
        """Retorna 404 cuando el grafo no existe."""
        response = client.get("/api/v1/graphs/nonexistent-project/article/10.1111%2Fa/neighbors")
        assert response.status_code == 404

    def test_neighbors_404_doi_not_found(self, client, mock_citation_graph):
        """Retorna 404 cuando el DOI no existe en el grafo."""
        _, project_id, _ = mock_citation_graph

        response = client.get(f"/api/v1/graphs/{project_id}/article/10.9999%2Fnonexistent/neighbors")
        assert response.status_code == 404


# ──────────────────────────────────────────────
# Tests de modelos Pydantic
# ──────────────────────────────────────────────

class TestPydanticModels:
    """Tests de validación de modelos Pydantic."""

    def test_graph_node_validates_required_fields(self):
        """GraphNode valida campos requeridos."""
        from app.models.graph_models import GraphNode

        node = GraphNode(id="10.1111/a", label="Test (2020)")
        assert node.id == "10.1111/a"
        assert node.label == "Test (2020)"
        assert node.status == "unknown"
        assert node.size == 15

    def test_graph_edge_validates_alias(self):
        """GraphEdge valida alias from → from_node."""
        from app.models.graph_models import GraphEdge

        edge = GraphEdge(**{"from": "A", "to": "B"})
        assert edge.from_node == "A"
        assert edge.to == "B"

    def test_graph_response_validates_complete(self):
        """GraphResponse valida respuesta completa."""
        from app.models.graph_models import GraphResponse, GraphNode, GraphEdge, GraphMetadata

        response = GraphResponse(
            graph_type="citation",
            project_id="test",
            nodes=[GraphNode(id="A", label="A")],
            edges=[GraphEdge(**{"from": "A", "to": "B"})],
            metadata=GraphMetadata(total_nodes=1, total_edges=1),
        )

        assert response.graph_type == "citation"
        assert len(response.nodes) == 1
        assert len(response.edges) == 1

    def test_graph_stats_response_validates(self):
        """GraphStatsResponse valida correctamente."""
        from app.models.graph_models import GraphStatsResponse

        stats = GraphStatsResponse(
            project_id="test",
            citation_graph={"total_nodes": 5},
            thematic_graph={"total_nodes": 3},
            total_included_articles=5,
            total_references=10,
            build_status="ready",
        )

        assert stats.build_status == "ready"
        assert stats.total_included_articles == 5

    def test_neighbor_response_validates(self):
        """NeighborResponse valida correctamente."""
        from app.models.graph_models import NeighborResponse, GraphNode, GraphEdge

        resp = NeighborResponse(
            nodes=[GraphNode(id="A", label="A")],
            edges=[GraphEdge(**{"from": "A", "to": "B"})],
        )

        assert len(resp.nodes) == 1
        assert len(resp.edges) == 1
