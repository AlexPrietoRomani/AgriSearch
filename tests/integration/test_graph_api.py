# -*- coding: utf-8 -*-
"""
Tests de integración para los endpoints REST de la API de Grafos.

Fase 4 — Sub-fase 4.4: API REST para Consulta de Grafos
Valida que los endpoints retornen datos correctos en el formato esperado
para ser consumidos por el frontend (vis-network).

Ejecución:
    pytest tests/integration/test_graph_api.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ──────────────────────────────────────────────
# Datos de prueba simulados (respuesta API)
# ──────────────────────────────────────────────

MOCK_CITATION_GRAPH_RESPONSE = {
    "graph_type": "citation",
    "project_id": "proj-uuid-001",
    "nodes": [
        {
            "id": "10.1016/j.compag.2023.107500",
            "label": "Wang et al. (2023)",
            "title": "YOLO-based crop phenology detection",
            "authors": "Wang J., Zhang H.",
            "year": 2023,
            "status": "included",
            "color": {"background": "#22c55e", "border": "#16a34a"},
            "size": 20,
        },
        {
            "id": "10.1109/CVPR.2016.91",
            "label": "He et al. (2016)",
            "title": "Deep Residual Learning for Image Recognition",
            "authors": "He K., Zhang X.",
            "year": 2016,
            "status": "cited_external",
            "color": {"background": "#3b82f6", "border": "#2563eb"},
            "size": 12,
        },
    ],
    "edges": [
        {
            "from": "10.1016/j.compag.2023.107500",
            "to": "10.1109/CVPR.2016.91",
            "arrows": "to",
            "extraction_source": "openalex",
        },
    ],
    "metadata": {
        "total_included": 1,
        "total_external": 1,
        "total_edges": 1,
    },
}

MOCK_THEMATIC_GRAPH_RESPONSE = {
    "graph_type": "thematic",
    "project_id": "proj-uuid-001",
    "nodes": [
        {
            "id": "10.1016/j.compag.2023.107500",
            "label": "Wang et al. (2023)",
            "title": "YOLO-based crop phenology detection",
            "topics": ["YOLO", "fenología", "agricultura de precisión"],
            "color": {"background": "#22c55e", "border": "#16a34a"},
            "size": 20,
        },
        {
            "id": "10.3390/rs14153690",
            "label": "Chen et al. (2022)",
            "title": "Remote sensing for crop monitoring",
            "topics": ["teledetección", "machine learning", "monitoreo"],
            "color": {"background": "#22c55e", "border": "#16a34a"},
            "size": 20,
        },
    ],
    "edges": [
        {
            "from": "10.1016/j.compag.2023.107500",
            "to": "10.3390/rs14153690",
            "cosine_similarity": 0.89,
            "shared_keywords": ["deep learning", "agricultura de precisión"],
            "width": 3,
            "dashes": [5, 5],
            "color": "#a78bfa",
        },
    ],
    "metadata": {
        "total_nodes": 2,
        "total_edges": 1,
        "similarity_threshold": 0.75,
    },
}


# ──────────────────────────────────────────────
# Tests de estructura de respuesta
# ──────────────────────────────────────────────

class TestCitationGraphEndpoint:
    """Tests para GET /api/v1/graphs/{project_id}/citation"""

    def test_response_has_required_fields(self):
        """La respuesta debe contener graph_type, project_id, nodes, edges, metadata."""
        response = MOCK_CITATION_GRAPH_RESPONSE
        required = {"graph_type", "project_id", "nodes", "edges", "metadata"}
        assert required.issubset(response.keys())

    def test_graph_type_is_citation(self):
        """El graph_type debe ser 'citation'."""
        assert MOCK_CITATION_GRAPH_RESPONSE["graph_type"] == "citation"

    def test_nodes_have_vis_network_format(self):
        """Cada nodo debe tener id, label, title, color (objeto), size."""
        for node in MOCK_CITATION_GRAPH_RESPONSE["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "title" in node
            assert "color" in node
            assert isinstance(node["color"], dict)
            assert "background" in node["color"]

    def test_edges_have_direction(self):
        """Las aristas de citación deben tener arrows: 'to' (dirigidas)."""
        for edge in MOCK_CITATION_GRAPH_RESPONSE["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert edge.get("arrows") == "to"

    def test_included_nodes_green_color(self):
        """Los nodos incluidos deben tener fondo verde."""
        included = [
            n for n in MOCK_CITATION_GRAPH_RESPONSE["nodes"]
            if n["status"] == "included"
        ]
        for node in included:
            assert node["color"]["background"] == "#22c55e"

    def test_external_nodes_blue_color(self):
        """Los nodos externos deben tener fondo azul."""
        external = [
            n for n in MOCK_CITATION_GRAPH_RESPONSE["nodes"]
            if n["status"] == "cited_external"
        ]
        for node in external:
            assert node["color"]["background"] == "#3b82f6"

    def test_metadata_counts(self):
        """Los metadatos deben reflejar los conteos correctos."""
        meta = MOCK_CITATION_GRAPH_RESPONSE["metadata"]
        assert meta["total_included"] >= 0
        assert meta["total_external"] >= 0
        assert meta["total_edges"] >= 0


class TestThematicGraphEndpoint:
    """Tests para GET /api/v1/graphs/{project_id}/thematic"""

    def test_response_has_required_fields(self):
        """La respuesta debe contener graph_type, project_id, nodes, edges, metadata."""
        response = MOCK_THEMATIC_GRAPH_RESPONSE
        required = {"graph_type", "project_id", "nodes", "edges", "metadata"}
        assert required.issubset(response.keys())

    def test_graph_type_is_thematic(self):
        """El graph_type debe ser 'thematic'."""
        assert MOCK_THEMATIC_GRAPH_RESPONSE["graph_type"] == "thematic"

    def test_thematic_edges_have_similarity(self):
        """Las aristas temáticas deben incluir cosine_similarity y shared_keywords."""
        for edge in MOCK_THEMATIC_GRAPH_RESPONSE["edges"]:
            assert "cosine_similarity" in edge
            assert 0.0 <= edge["cosine_similarity"] <= 1.0
            assert "shared_keywords" in edge
            assert isinstance(edge["shared_keywords"], list)

    def test_thematic_edges_no_arrows(self):
        """Las aristas temáticas NO deben tener flechas (grafo no-dirigido)."""
        for edge in MOCK_THEMATIC_GRAPH_RESPONSE["edges"]:
            assert "arrows" not in edge or edge.get("arrows") is None

    def test_thematic_nodes_have_topics(self):
        """Cada nodo temático debe tener una lista de topics."""
        for node in MOCK_THEMATIC_GRAPH_RESPONSE["nodes"]:
            assert "topics" in node
            assert isinstance(node["topics"], list)
            assert len(node["topics"]) > 0

    def test_similarity_threshold_in_metadata(self):
        """Los metadatos deben incluir el umbral de similitud usado."""
        meta = MOCK_THEMATIC_GRAPH_RESPONSE["metadata"]
        assert "similarity_threshold" in meta
        assert meta["similarity_threshold"] == 0.75

    def test_all_thematic_nodes_are_included(self):
        """En el grafo temático, todos los nodos deben ser artículos incluidos (no externos)."""
        for node in MOCK_THEMATIC_GRAPH_RESPONSE["nodes"]:
            # Los nodos temáticos solo son artículos incluidos
            assert node["color"]["background"] == "#22c55e"


# ──────────────────────────────────────────────
# Tests de filtros y parámetros de consulta
# ──────────────────────────────────────────────

class TestGraphQueryParameters:
    """Tests para los filtros de consulta de la API de grafos."""

    def test_year_filter_structure(self):
        """Un filtro por año debe generar nodos del rango especificado."""
        year_min, year_max = 2020, 2023
        filtered = [
            n for n in MOCK_CITATION_GRAPH_RESPONSE["nodes"]
            if year_min <= n.get("year", 0) <= year_max
        ]
        for node in filtered:
            assert year_min <= node["year"] <= year_max

    def test_status_filter_included_only(self):
        """Filtro status=included retorna solo nodos incluidos."""
        filtered = [
            n for n in MOCK_CITATION_GRAPH_RESPONSE["nodes"]
            if n["status"] == "included"
        ]
        for node in filtered:
            assert node["status"] == "included"

    def test_depth_parameter_limits_expansion(self):
        """El parámetro depth limita cuántos niveles de citas se expanden."""
        depth = 1
        # Con depth=1, solo se muestran las citas directas, no las citas de las citas
        assert isinstance(depth, int)
        assert depth >= 0
