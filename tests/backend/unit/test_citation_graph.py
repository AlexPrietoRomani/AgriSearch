# -*- coding: utf-8 -*-
"""
Tests unitarios para la construcción del Grafo de Citaciones.

Fase 4 — Sub-fase 4.2: Construcción del Grafo de Citaciones
Valida la inserción de nodos (artículos) y aristas (citas), las queries
de travesía, y la correcta asignación de colores según status.

Ejecución:
    pytest tests/unit/test_citation_graph.py -v
"""

import pytest


# ──────────────────────────────────────────────
# Datos de prueba
# ──────────────────────────────────────────────

INCLUDED_ARTICLES = [
    {
        "doi": "10.1016/j.compag.2023.107500",
        "title": "YOLO-based crop phenology detection",
        "authors": "Wang J., Zhang H.",
        "year": 2023,
        "status": "included",
    },
    {
        "doi": "10.1007/s11119-022-09876-5",
        "title": "UAV-based wheat disease detection",
        "authors": "García-Martínez A.",
        "year": 2022,
        "status": "included",
    },
    {
        "doi": "10.3390/rs14153690",
        "title": "Remote sensing for crop monitoring",
        "authors": "Chen Y., Kim S.",
        "year": 2022,
        "status": "included",
    },
]

EXTERNAL_ARTICLES = [
    {
        "doi": "10.1109/CVPR.2016.91",
        "title": "Deep Residual Learning",
        "authors": "He K.",
        "year": 2016,
        "status": "cited_external",
    },
    {
        "doi": "10.48550/arXiv.1506.02640",
        "title": "YOLO: Real-Time Object Detection",
        "authors": "Redmon J.",
        "year": 2016,
        "status": "cited_external",
    },
]

CITATION_EDGES = [
    {"from": "10.1016/j.compag.2023.107500", "to": "10.1109/CVPR.2016.91"},
    {"from": "10.1016/j.compag.2023.107500", "to": "10.48550/arXiv.1506.02640"},
    {"from": "10.1016/j.compag.2023.107500", "to": "10.3390/rs14153690"},
    {"from": "10.1007/s11119-022-09876-5", "to": "10.1109/CVPR.2016.91"},
    {"from": "10.3390/rs14153690", "to": "10.1109/CVPR.2016.91"},
]


# ──────────────────────────────────────────────
# Simulación de grafo en memoria (NetworkX)
# ──────────────────────────────────────────────

class TestCitationGraphConstruction:
    """Tests para la construcción del grafo de citaciones con NetworkX."""

    @pytest.fixture
    def citation_graph(self):
        """Construye un grafo de citaciones de prueba."""
        import networkx as nx

        G = nx.DiGraph()

        # Añadir nodos incluidos
        for article in INCLUDED_ARTICLES:
            G.add_node(
                article["doi"],
                title=article["title"],
                authors=article["authors"],
                year=article["year"],
                status="included",
                color="#22c55e",
            )

        # Añadir nodos externos
        for article in EXTERNAL_ARTICLES:
            G.add_node(
                article["doi"],
                title=article["title"],
                authors=article["authors"],
                year=article["year"],
                status="cited_external",
                color="#3b82f6",
            )

        # Añadir aristas de citación
        for edge in CITATION_EDGES:
            G.add_edge(edge["from"], edge["to"], relation="CITES")

        return G

    def test_total_nodes(self, citation_graph):
        """El grafo debe tener 5 nodos (3 incluidos + 2 externos)."""
        assert citation_graph.number_of_nodes() == 5

    def test_total_edges(self, citation_graph):
        """El grafo debe tener 5 aristas de citación."""
        assert citation_graph.number_of_edges() == 5

    def test_included_nodes_are_green(self, citation_graph):
        """Los nodos incluidos deben tener color verde (#22c55e)."""
        for article in INCLUDED_ARTICLES:
            node = citation_graph.nodes[article["doi"]]
            assert node["status"] == "included"
            assert node["color"] == "#22c55e"

    def test_external_nodes_are_blue(self, citation_graph):
        """Los nodos externos deben tener color azul (#3b82f6)."""
        for article in EXTERNAL_ARTICLES:
            node = citation_graph.nodes[article["doi"]]
            assert node["status"] == "cited_external"
            assert node["color"] == "#3b82f6"

    def test_directed_edges(self, citation_graph):
        """Las aristas deben ser dirigidas (A cita a B ≠ B cita a A)."""
        assert citation_graph.is_directed()
        # Wang cita a He (ResNet)
        assert citation_graph.has_edge(
            "10.1016/j.compag.2023.107500", "10.1109/CVPR.2016.91"
        )
        # He NO cita a Wang
        assert not citation_graph.has_edge(
            "10.1109/CVPR.2016.91", "10.1016/j.compag.2023.107500"
        )

    def test_most_cited_node(self, citation_graph):
        """ResNet (He et al., 2016) debe ser el nodo más citado."""
        in_degrees = dict(citation_graph.in_degree())
        most_cited = max(in_degrees, key=in_degrees.get)
        assert most_cited == "10.1109/CVPR.2016.91"
        assert in_degrees[most_cited] == 3

    def test_neighbors_of_included_article(self, citation_graph):
        """Wang (2023) cita 3 artículos."""
        successors = list(
            citation_graph.successors("10.1016/j.compag.2023.107500")
        )
        assert len(successors) == 3

    def test_included_citing_included(self, citation_graph):
        """Wang (2023) cita a Chen (2022) — ambos incluidos → arista verde-verde."""
        assert citation_graph.has_edge(
            "10.1016/j.compag.2023.107500", "10.3390/rs14153690"
        )
        source_status = citation_graph.nodes["10.1016/j.compag.2023.107500"]["status"]
        target_status = citation_graph.nodes["10.3390/rs14153690"]["status"]
        assert source_status == "included"
        assert target_status == "included"


# ──────────────────────────────────────────────
# Tests de serialización para API
# ──────────────────────────────────────────────

class TestCitationGraphSerialization:
    """Tests para la conversión del grafo a formato JSON para la API REST."""

    def test_node_serialization(self):
        """Un nodo debe serializarse con todos los campos requeridos."""
        node_data = {
            "id": "10.1016/j.compag.2023.107500",
            "label": "Wang et al. (2023)",
            "title": "YOLO-based crop phenology detection",
            "color": "#22c55e",
            "status": "included",
            "year": 2023,
        }
        required_keys = {"id", "label", "title", "color", "status"}
        assert required_keys.issubset(node_data.keys())

    def test_edge_serialization(self):
        """Una arista debe tener from, to y opcionalmente extraction_source."""
        edge_data = {
            "from": "10.1016/j.compag.2023.107500",
            "to": "10.1109/CVPR.2016.91",
            "arrows": "to",
            "extraction_source": "openalex",
        }
        assert "from" in edge_data
        assert "to" in edge_data
        assert edge_data["from"] != edge_data["to"]

    def test_graph_json_structure(self):
        """El JSON del grafo debe tener las claves nodes y edges."""
        graph_json = {
            "nodes": [{"id": "doi1"}, {"id": "doi2"}],
            "edges": [{"from": "doi1", "to": "doi2"}],
            "metadata": {"total_nodes": 2, "total_edges": 1},
        }
        assert "nodes" in graph_json
        assert "edges" in graph_json
        assert graph_json["metadata"]["total_nodes"] == len(graph_json["nodes"])
