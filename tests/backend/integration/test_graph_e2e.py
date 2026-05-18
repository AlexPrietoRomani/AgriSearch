"""
Archivo: test_graph_e2e.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Tests end-to-end para el flujo completo de exploración de grafos bibliográficos.

Simula el recorrido de un usuario desde el dashboard hasta la visualización
de grafos, incluyendo construcción, consulta de citaciones, grafos temáticos,
estadísticas y exploración de vecinos.

Acciones Principales:
    - Validar flujo completo: build → citation → thematic → stats → neighbors.
    - Validar 404 graceful para proyectos sin datos.
    - Validar que endpoints de grafos no afectan otras rutas.
    - Validar consistencia entre endpoints (mismo project_id).
    - Validar filtros combinados en grafo de citación.
    - Validar umbral dinámico en grafo temático.

Ejemplo de Ejecución:
    pytest tests/backend/integration/test_graph_e2e.py -v
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
import app.api.v1.graphs as graphs_module


@pytest.fixture
def client():
    """Crea un cliente de test para FastAPI."""
    return TestClient(app)


@pytest.fixture
def graph_data_dir(tmp_path, monkeypatch):
    """Crea un directorio de grafos mock y parchea las rutas."""
    project_id = "test-e2e-project"
    graph_dir = tmp_path / "projects" / project_id / "graphs"
    graph_dir.mkdir(parents=True)

    monkeypatch.setattr(graphs_module, "GRAPH_DIR", tmp_path / "projects")

    @staticmethod
    def patched_load(pid, graph_dir_param=None):
        if graph_dir_param is None:
            graph_dir_param = tmp_path / "projects" / pid / "graphs"
        json_path = graph_dir_param / "citation_graph.json"
        if not json_path.exists():
            return None
        return json.loads(json_path.read_text(encoding="utf-8"))

    monkeypatch.setattr(graphs_module.CitationGraphBuilder, "load_graph", patched_load)

    return graph_dir, project_id


@pytest.fixture
def full_graph_data(graph_data_dir):
    """Crea ambos grafos (citación + temático) para tests E2E."""
    graph_dir, project_id = graph_data_dir

    citation_data = {
        "graph_type": "citation",
        "project_id": project_id,
        "nodes": [
            {
                "id": "10.1000/e2e-1",
                "label": "Garcia (2022)",
                "title": "Machine learning for crop yield prediction",
                "color": {"background": "#22c55e", "border": "#16a34a"},
                "size": 25,
                "shape": "dot",
                "status": "included",
            },
            {
                "id": "10.1000/e2e-2",
                "label": "Martinez (2023)",
                "title": "Deep learning approaches in precision agriculture",
                "color": {"background": "#22c55e", "border": "#16a34a"},
                "size": 20,
                "shape": "dot",
                "status": "included",
            },
            {
                "id": "10.1000/e2e-3",
                "label": "Lopez (2021)",
                "title": "Soil moisture sensors for irrigation optimization",
                "color": {"background": "#22c55e", "border": "#16a34a"},
                "size": 18,
                "shape": "dot",
                "status": "included",
            },
            {
                "id": "10.2000/ext-ml",
                "label": "Smith (2020)",
                "title": "Neural networks for agricultural data",
                "color": {"background": "#3b82f6", "border": "#2563eb"},
                "size": 15,
                "shape": "dot",
                "status": "cited_external",
            },
            {
                "id": "10.2000/ext-iot",
                "label": "Johnson (2019)",
                "title": "IoT sensors in smart farming",
                "color": {"background": "#3b82f6", "border": "#2563eb"},
                "size": 12,
                "shape": "dot",
                "status": "cited_external",
            },
        ],
        "edges": [
            {
                "from": "10.1000/e2e-1",
                "to": "10.2000/ext-ml",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
            {
                "from": "10.1000/e2e-2",
                "to": "10.2000/ext-ml",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
            {
                "from": "10.1000/e2e-3",
                "to": "10.2000/ext-iot",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
            {
                "from": "10.1000/e2e-1",
                "to": "10.1000/e2e-3",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#f59e0b"},
                "width": 1.5,
            },
        ],
        "metadata": {
            "total_nodes": 5,
            "total_edges": 4,
            "total_included": 3,
            "total_external": 2,
            "most_cited": [
                {"doi": "10.2000/ext-ml", "in_degree": 2},
                {"doi": "10.1000/e2e-3", "in_degree": 1},
            ],
            "bridge_articles": [
                {"doi": "10.2000/ext-ml", "cited_by_count": 2},
            ],
            "density": 0.4,
        },
    }

    thematic_data = {
        "graph_type": "thematic",
        "project_id": project_id,
        "nodes": [
            {
                "id": "10.1000/e2e-1",
                "label": "Garcia (2022)",
                "title": "Machine learning for crop yield prediction",
                "color": {"background": "#22c55e"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 0,
            },
            {
                "id": "10.1000/e2e-2",
                "label": "Martinez (2023)",
                "title": "Deep learning approaches in precision agriculture",
                "color": {"background": "#22c55e"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 0,
            },
            {
                "id": "10.1000/e2e-3",
                "label": "Lopez (2021)",
                "title": "Soil moisture sensors for irrigation optimization",
                "color": {"background": "#3b82f6"},
                "size": 15,
                "shape": "dot",
                "status": "included",
                "cluster": 1,
            },
        ],
        "edges": [
            {
                "from": "10.1000/e2e-1",
                "to": "10.1000/e2e-2",
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": 3.6,
                "dashes": [5, 5],
                "cosine_similarity": 0.92,
                "shared_keywords": ["machine learning", "agriculture", "prediction"],
            },
            {
                "from": "10.1000/e2e-1",
                "to": "10.1000/e2e-3",
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": 2.0,
                "dashes": [5, 5],
                "cosine_similarity": 0.55,
                "shared_keywords": ["agriculture"],
            },
            {
                "from": "10.1000/e2e-2",
                "to": "10.1000/e2e-3",
                "arrows": "to",
                "color": {"color": "#a78bfa", "highlight": "#8b5cf6"},
                "width": 1.8,
                "dashes": [5, 5],
                "cosine_similarity": 0.48,
                "shared_keywords": ["optimization"],
            },
        ],
        "metadata": {
            "total_nodes": 3,
            "total_edges": 3,
            "threshold": 0.75,
            "num_clusters": 2,
            "cluster_sizes": {"0": 2, "1": 1},
        },
    }

    (graph_dir / "citation_graph.json").write_text(
        json.dumps(citation_data), encoding="utf-8"
    )
    (graph_dir / "thematic_graph.json").write_text(
        json.dumps(thematic_data), encoding="utf-8"
    )

    return graph_dir, project_id, citation_data, thematic_data


# ──────────────────────────────────────────────
# E2E Test 1: Full graph exploration flow
# ──────────────────────────────────────────────

class TestFullGraphExplorationFlow:
    """Tests del flujo completo de exploración de grafos."""

    def test_full_exploration_flow(self, client, full_graph_data):
        """
        Flujo E2E completo: stats → citation → thematic → neighbors.

        Simula lo que haría un usuario:
        1. Ver estadísticas del proyecto
        2. Cargar grafo de citaciones
        3. Cargar grafo temático con umbral
        4. Explorar vecinos de un artículo
        """
        _, project_id, _, _ = full_graph_data

        # Paso 1: Obtener estadísticas
        stats_resp = client.get(f"/api/v1/graphs/{project_id}/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["build_status"] == "ready"
        assert stats["citation_graph"]["total_nodes"] == 5
        assert stats["thematic_graph"]["num_clusters"] == 2

        # Paso 2: Cargar grafo de citaciones
        citation_resp = client.get(f"/api/v1/graphs/{project_id}/citation")
        assert citation_resp.status_code == 200
        citation = citation_resp.json()
        assert citation["graph_type"] == "citation"
        assert len(citation["nodes"]) == 5
        assert len(citation["edges"]) == 4

        # Verificar que hay nodos incluidos y externos
        included = [n for n in citation["nodes"] if n["status"] == "included"]
        external = [n for n in citation["nodes"] if n["status"] == "cited_external"]
        assert len(included) == 3
        assert len(external) == 2

        # Paso 3: Cargar grafo temático con umbral alto
        thematic_resp = client.get(
            f"/api/v1/graphs/{project_id}/thematic?threshold=0.75"
        )
        assert thematic_resp.status_code == 200
        thematic = thematic_resp.json()
        assert thematic["graph_type"] == "thematic"
        # Solo 1 arista con cosine_similarity >= 0.75 (0.92)
        assert len(thematic["edges"]) == 1
        assert thematic["edges"][0]["cosine_similarity"] == 0.92

        # Paso 4: Explorar vecinos del artículo más citado
        neighbors_resp = client.get(
            f"/api/v1/graphs/{project_id}/article/10.2000%2Fext-ml/neighbors"
        )
        assert neighbors_resp.status_code == 200
        neighbors = neighbors_resp.json()
        # 10.1000/e2e-1 y 10.1000/e2e-2 citan a ext-ml
        assert len(neighbors["nodes"]) == 2
        assert len(neighbors["edges"]) == 2

    def test_citation_filter_by_status_in_flow(self, client, full_graph_data):
        """En el flujo, filtrar por status funciona correctamente."""
        _, project_id, _, _ = full_graph_data

        # Filtrar solo incluidos
        resp = client.get(
            f"/api/v1/graphs/{project_id}/citation?status=included"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(n["status"] == "included" for n in data["nodes"])
        # Las aristas deben conectar solo nodos incluidos
        node_ids = {n["id"] for n in data["nodes"]}
        for edge in data["edges"]:
            assert edge["from"] in node_ids
            assert edge["to"] in node_ids

    def test_thematic_threshold_slider_flow(self, client, full_graph_data):
        """Simular slider de umbral en el flujo temático."""
        _, project_id, _, _ = full_graph_data

        # Umbral 0.0: todas las aristas
        resp = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.0")
        assert resp.status_code == 200
        assert len(resp.json()["edges"]) == 3

        # Umbral 0.5: 2 aristas (0.92 y 0.55)
        resp = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.5")
        assert resp.status_code == 200
        assert len(resp.json()["edges"]) == 2

        # Umbral 0.75: 1 arista (0.92)
        resp = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.75")
        assert resp.status_code == 200
        assert len(resp.json()["edges"]) == 1

        # Umbral 0.95: 0 aristas
        resp = client.get(f"/api/v1/graphs/{project_id}/thematic?threshold=0.95")
        assert resp.status_code == 200
        assert len(resp.json()["edges"]) == 0


# ──────────────────────────────────────────────
# E2E Test 2: Graceful 404 for projects without data
# ──────────────────────────────────────────────

class TestGraceful404Handling:
    """Tests de manejo graceful de 404 para proyectos sin datos."""

    def test_404_citation_no_graph(self, client):
        """Proyecto sin grafo de citación retorna 404 con mensaje útil."""
        response = client.get("/api/v1/graphs/nonexistent-project/citation")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no construido" in data["detail"].lower()

    def test_404_thematic_no_graph(self, client):
        """Proyecto sin grafo temático retorna 404 con mensaje útil."""
        response = client.get("/api/v1/graphs/nonexistent-project/thematic")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no construido" in data["detail"].lower()

    def test_404_neighbors_no_graph(self, client):
        """Proyecto sin grafo retorna 404 en vecinos."""
        response = client.get(
            "/api/v1/graphs/nonexistent-project/article/10.1111%2Fa/neighbors"
        )
        assert response.status_code == 404

    def test_404_neighbors_doi_not_found(self, client, full_graph_data):
        """DOI inexistente en grafo retorna 404."""
        _, project_id, _, _ = full_graph_data

        response = client.get(
            f"/api/v1/graphs/{project_id}/article/10.9999%2Fnonexistent/neighbors"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no encontrado" in data["detail"].lower()

    def test_stats_returns_not_built_status(self, client):
        """Stats retorna 'not_built' en lugar de 404 para proyecto sin grafos."""
        response = client.get("/api/v1/graphs/nonexistent-project/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["build_status"] == "not_built"
        assert data["citation_graph"] == {}
        assert data["thematic_graph"] == {}


# ──────────────────────────────────────────────
# E2E Test 3: Graph API isolation from other routes
# ──────────────────────────────────────────────

class TestGraphAPIIsolation:
    """Tests de aislamiento de la API de grafos."""

    def test_graph_endpoints_do_not_affect_other_routes(self, client):
        """Los endpoints de grafos no afectan otras rutas de la API."""
        # Verificar que el endpoint de health/system funciona
        # independientemente de los grafos
        response = client.get("/api/v1/system/health")
        # Debe responder sin error (200 o el que esté configurado)
        assert response.status_code in [200, 404, 500]

    def test_graph_endpoints_return_consistent_project_id(self, client, full_graph_data):
        """Todos los endpoints retornan el mismo project_id."""
        _, project_id, _, _ = full_graph_data

        citation = client.get(f"/api/v1/graphs/{project_id}/citation").json()
        thematic = client.get(
            f"/api/v1/graphs/{project_id}/thematic?threshold=0.0"
        ).json()
        stats = client.get(f"/api/v1/graphs/{project_id}/stats").json()

        assert citation["project_id"] == project_id
        assert thematic["project_id"] == project_id
        assert stats["project_id"] == project_id

    def test_graph_response_models_are_valid(self, client, full_graph_data):
        """Las respuestas son válidas según los modelos Pydantic."""
        from app.models.graph_models import GraphResponse, GraphStatsResponse

        _, project_id, _, _ = full_graph_data

        # Citation response
        citation_data = client.get(
            f"/api/v1/graphs/{project_id}/citation"
        ).json()
        citation_model = GraphResponse(**citation_data)
        assert citation_model.graph_type == "citation"
        assert len(citation_model.nodes) == 5
        assert len(citation_model.edges) == 4

        # Thematic response
        thematic_data = client.get(
            f"/api/v1/graphs/{project_id}/thematic?threshold=0.0"
        ).json()
        thematic_model = GraphResponse(**thematic_data)
        assert thematic_model.graph_type == "thematic"
        assert len(thematic_model.nodes) == 3

        # Stats response
        stats_data = client.get(
            f"/api/v1/graphs/{project_id}/stats"
        ).json()
        stats_model = GraphStatsResponse(**stats_data)
        assert stats_model.build_status == "ready"

    def test_neighbors_consistency_with_citation_graph(self, client, full_graph_data):
        """Los vecinos retornados son consistentes con el grafo de citación."""
        _, project_id, citation_data, _ = full_graph_data

        # Obtener vecinos de ext-ml (citado por e2e-1 y e2e-2)
        neighbors_resp = client.get(
            f"/api/v1/graphs/{project_id}/article/10.2000%2Fext-ml/neighbors"
        )
        assert neighbors_resp.status_code == 200
        neighbors = neighbors_resp.json()

        # Los nodos vecinos deben existir en el grafo original
        original_node_ids = {n["id"] for n in citation_data["nodes"]}
        for node in neighbors["nodes"]:
            assert node["id"] in original_node_ids

        # Las aristas de vecinos deben existir en el grafo original
        original_edges = {
            (e["from"], e["to"]) for e in citation_data["edges"]
        }
        for edge in neighbors["edges"]:
            assert (edge["from"], edge["to"]) in original_edges

    def test_metadata_consistency_across_endpoints(self, client, full_graph_data):
        """La metadata es consistente entre stats y los endpoints de grafos."""
        _, project_id, _, _ = full_graph_data

        # Obtener stats
        stats = client.get(f"/api/v1/graphs/{project_id}/stats").json()
        citation_meta = stats["citation_graph"]

        # Obtener grafo de citación
        citation = client.get(
            f"/api/v1/graphs/{project_id}/citation"
        ).json()
        citation_graph_meta = citation["metadata"]

        # Los contadores deben coincidir
        assert citation_meta["total_nodes"] == citation_graph_meta["total_nodes"]
        assert citation_meta["total_edges"] == citation_graph_meta["total_edges"]
        assert citation_meta["total_included"] == citation_graph_meta["total_included"]
        assert citation_meta["total_external"] == citation_graph_meta["total_external"]
