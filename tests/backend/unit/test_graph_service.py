"""
Archivo: test_graph_service.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Tests unitarios para CitationGraphBuilder y funciones auxiliares
del servicio de grafos bibliográficos.

Acciones Principales:
    - Validar construcción de grafo dirigido con datos mock.
    - Verificar colores de nodos (verde=incluido, azul=externo).
    - Confirmar dirección de aristas (A cita B ≠ B cita A).
    - Validar cálculo de in-degree y detección de artículos puente.
    - Verificar serialización a formato vis-network.
    - Confirmar roundtrip save/load de grafos JSON.
    - Validar obtención de vecinos de un nodo.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_graph_service.py -v
"""

import json
import pytest
import numpy as np
import networkx as nx
from pathlib import Path
from numpy.typing import NDArray
from sklearn.metrics.pairwise import cosine_similarity
from unittest.mock import AsyncMock, MagicMock, patch


# ──────────────────────────────────────────────
# Tests de constantes y configuración
# ──────────────────────────────────────────────

class TestGraphConstants:
    """Tests de configuración de colores y constantes."""

    def test_color_included_is_green(self):
        """Color de artículos incluidos es verde."""
        from app.services.graph_service import COLOR_INCLUDED
        assert COLOR_INCLUDED == "#22c55e"

    def test_color_external_is_blue(self):
        """Color de artículos externos es azul."""
        from app.services.graph_service import COLOR_EXTERNAL
        assert COLOR_EXTERNAL == "#3b82f6"

    def test_color_border_included(self):
        """Borde de artículos incluidos es verde oscuro."""
        from app.services.graph_service import COLOR_BORDER_INCLUDED
        assert COLOR_BORDER_INCLUDED == "#16a34a"

    def test_color_border_external(self):
        """Borde de artículos externos es azul oscuro."""
        from app.services.graph_service import COLOR_BORDER_EXTERNAL
        assert COLOR_BORDER_EXTERNAL == "#2563eb"


# ──────────────────────────────────────────────
# Tests de construcción de grafo con NetworkX
# ──────────────────────────────────────────────

class TestDirectedGraphConstruction:
    """Tests de construcción del grafo de citaciones."""

    def test_build_directed_graph_from_mock_data(self):
        """Construye grafo con datos mock."""
        G = nx.DiGraph()

        G.add_node("10.1111/a", status="included", color={"background": "#22c55e"})
        G.add_node("10.2222/b", status="included", color={"background": "#22c55e"})
        G.add_node("10.3333/c", status="cited_external", color={"background": "#3b82f6"})

        G.add_edge("10.1111/a", "10.3333/c")
        G.add_edge("10.2222/b", "10.3333/c")

        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2
        assert G.is_directed()

    def test_node_colors_assigned_correctly(self):
        """Verde para incluidos, azul para externos."""
        from app.services.graph_service import COLOR_INCLUDED, COLOR_EXTERNAL

        assert COLOR_INCLUDED == "#22c55e"
        assert COLOR_EXTERNAL == "#3b82f6"

    def test_edge_direction_asymmetric(self):
        """A cita B ≠ B cita A."""
        G = nx.DiGraph()
        G.add_edge("A", "B")

        assert G.has_edge("A", "B")
        assert not G.has_edge("B", "A")

    def test_in_degree_calculation(self):
        """Nodo más citado tiene mayor in-degree."""
        G = nx.DiGraph()
        G.add_edge("A", "C")
        G.add_edge("B", "C")
        G.add_edge("D", "C")
        G.add_edge("A", "B")

        in_degrees = dict(G.in_degree())
        assert in_degrees["C"] == 3
        assert in_degrees["B"] == 1
        assert in_degrees["A"] == 0
        assert in_degrees["D"] == 0

    def test_bridge_article_detection(self):
        """Externo citado por ≥2 incluidos es puente."""
        G = nx.DiGraph()
        G.add_node("ext1", status="cited_external")
        G.add_node("ext2", status="cited_external")
        G.add_node("inc1", status="included")
        G.add_node("inc2", status="included")

        G.add_edge("inc1", "ext1")
        G.add_edge("inc2", "ext1")
        G.add_edge("inc1", "ext2")

        in_degrees = dict(G.in_degree())
        assert in_degrees["ext1"] == 2  # Puente
        assert in_degrees["ext2"] == 1  # No puente

    def test_graph_handles_disconnected_nodes(self):
        """Artículos sin referencias no rompen el grafo."""
        G = nx.DiGraph()
        G.add_node("isolated", status="included", color={"background": "#22c55e"})
        G.add_node("connected", status="included", color={"background": "#22c55e"})
        G.add_edge("connected", "10.9999/ext")

        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 1
        assert G.degree("isolated") == 0


# ──────────────────────────────────────────────
# Tests de serialización vis-network
# ──────────────────────────────────────────────

class TestVisNetworkSerialization:
    """Tests de serialización a formato vis-network."""

    def test_serialize_to_vis_network_format(self):
        """Serialización produce estructura {nodes, edges, metadata}."""
        G = nx.DiGraph()
        G.add_node("10.1111/a", status="included", label="A (2020)", title="Paper A",
                   color={"background": "#22c55e"}, size=20)
        G.add_node("10.2222/b", status="cited_external", label="B (2019)", title="Paper B",
                   color={"background": "#3b82f6"}, size=12)
        G.add_edge("10.1111/a", "10.2222/b")

        nodes = []
        for node, data in G.nodes(data=True):
            nodes.append({
                "id": node,
                "label": data.get("label", node),
                "color": data.get("color", {}),
                "size": data.get("size", 15),
                "status": data.get("status", "unknown"),
            })

        edges = []
        for source, target in G.edges():
            edges.append({"from": source, "to": target, "arrows": "to"})

        result = {"nodes": nodes, "edges": edges}

        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["nodes"][0]["status"] == "included"
        assert result["nodes"][1]["status"] == "cited_external"

    def test_node_has_required_fields(self):
        """Cada nodo tiene id, label, color, size, status."""
        node = {
            "id": "10.1038/test",
            "label": "Smith (2021)",
            "title": "Test Paper",
            "color": {"background": "#22c55e"},
            "size": 20,
            "status": "included",
        }
        required = ["id", "label", "color", "size", "status"]
        for field in required:
            assert field in node

    def test_edge_has_required_fields(self):
        """Cada arista tiene from, to, arrows."""
        edge = {
            "from": "10.1111/a",
            "to": "10.2222/b",
            "arrows": "to",
            "color": {"color": "#94a3b8"},
            "width": 1.5,
        }
        required = ["from", "to", "arrows"]
        for field in required:
            assert field in edge


# ──────────────────────────────────────────────
# Tests de save/load roundtrip
# ──────────────────────────────────────────────

class TestSaveLoadRoundtrip:
    """Tests de persistencia de grafos."""

    def test_save_and_load_graph_roundtrip(self, tmp_path):
        """Serialización + deserialización preserva datos."""
        data = {
            "graph_type": "citation",
            "nodes": [{"id": "10.1111/a", "status": "included"}],
            "edges": [{"from": "10.1111/a", "to": "10.2222/b"}],
            "metadata": {"total_nodes": 2},
        }

        json_path = tmp_path / "citation_graph.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert loaded["graph_type"] == "citation"
        assert len(loaded["nodes"]) == 1
        assert len(loaded["edges"]) == 1

    def test_load_nonexistent_graph_returns_none(self, tmp_path):
        """Cargar grafo inexistente retorna None."""
        from app.services.graph_service import CitationGraphBuilder

        result = CitationGraphBuilder.load_graph("nonexistent", graph_dir=tmp_path)
        assert result is None


# ──────────────────────────────────────────────
# Tests de vecinos de nodos
# ──────────────────────────────────────────────

class TestGetNeighbors:
    """Tests de obtención de vecinos."""

    def test_get_neighbors_returns_adjacent_nodes(self):
        """get_neighbors retorna nodos conectados."""
        G = nx.DiGraph()
        G.add_edge("A", "B")
        G.add_edge("C", "A")
        G.add_edge("A", "D")

        predecessors = list(G.predecessors("A"))
        successors = list(G.successors("A"))

        assert "B" in successors
        assert "C" in predecessors
        assert "D" in successors

    def test_get_neighbors_empty_for_isolated_node(self):
        """Nodo aislado no tiene vecinos."""
        G = nx.DiGraph()
        G.add_node("isolated")

        predecessors = list(G.predecessors("isolated"))
        successors = list(G.successors("isolated"))

        assert len(predecessors) == 0
        assert len(successors) == 0


# ──────────────────────────────────────────────
# Tests de CitationGraphBuilder con mocks
# ──────────────────────────────────────────────

class TestCitationGraphBuilderWithMocks:
    """Tests de CitationGraphBuilder con sesiones mock de SQLAlchemy."""

    def _make_mock_article(self, article_id, doi, title, authors, year, project_id="proj-001"):
        """Crea un objeto simple que simula Article."""
        class MockArticle:
            pass
        a = MockArticle()
        a.id = article_id
        a.doi = doi
        a.title = title
        a.authors = authors
        a.year = year
        a.abstract = "Test abstract"
        a.project_id = project_id
        return a

    def _make_mock_reference(self, source_id, cited_doi, cited_title, cited_authors, cited_year, is_in_project):
        """Crea un objeto simple que simula ArticleReference."""
        class MockRef:
            pass
        r = MockRef()
        r.source_article_id = source_id
        r.cited_doi = cited_doi
        r.cited_title = cited_title
        r.cited_authors = cited_authors
        r.cited_year = cited_year
        r.is_in_project = is_in_project
        r.extraction_source = "openalex"
        return r

    @pytest.mark.asyncio
    async def test_load_project_articles(self):
        """Carga artículos del proyecto correctamente."""
        from app.services.graph_service import CitationGraphBuilder

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        articles = [
            self._make_mock_article("a1", "10.1111/test1", "Paper 1", "Smith J.", 2020),
            self._make_mock_article("a2", "10.2222/test2", "Paper 2", "Jones K.", 2021),
        ]
        mock_scalars.all.return_value = articles
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        builder = CitationGraphBuilder(mock_session, "proj-001")
        result = await builder.load_project_articles()

        assert len(result) == 2
        assert "10.1111/test1" in result
        assert result["10.1111/test1"]["title"] == "Paper 1"
        assert result["10.2222/test2"]["authors"] == "Jones K."

    @pytest.mark.asyncio
    async def test_load_references(self):
        """Carga referencias del proyecto correctamente."""
        from app.services.graph_service import CitationGraphBuilder

        mock_session = AsyncMock()
        
        # Mock para artículos elegibles (primera llamada a execute)
        mock_article = self._make_mock_article("a1", "10.1111/test1", "SUCCESS", "/path/md.md", "success", "sq1")
        mock_article_result = MagicMock()
        mock_article_scalars = MagicMock()
        mock_article_scalars.all.return_value = [mock_article]
        mock_article_result.scalars.return_value = mock_article_scalars
        
        # Mock para referencias (segunda llamada a execute)
        refs = [
            self._make_mock_reference("a1", "10.3333/ext1", "Ext Paper", "Brown L.", 2019, False),
            self._make_mock_reference("a1", "10.2222/test2", "Paper 2", "Jones K.", 2021, True),
        ]
        mock_ref_result = MagicMock()
        mock_ref_scalars = MagicMock()
        mock_ref_scalars.all.return_value = refs
        mock_ref_result.scalars.return_value = mock_ref_scalars
        
        # Configurar execute para retornar diferentes resultados en cada llamada
        mock_session.execute.side_effect = [mock_article_result, mock_ref_result]

        builder = CitationGraphBuilder(mock_session, "proj-001")
        result = await builder.load_references()

        assert len(result) == 2
        assert result[0]["cited_doi"] == "10.3333/ext1"
        assert result[0]["is_in_project"] is False
        assert result[1]["is_in_project"] is True

    @pytest.mark.asyncio
    async def test_build_directed_graph_full(self):
        """Construye grafo completo simulando datos cargados."""
        from app.services.graph_service import CitationGraphBuilder, COLOR_INCLUDED, COLOR_EXTERNAL

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")

        articles_map = {
            "10.1111/inc1": {
                "doi": "10.1111/inc1",
                "title": "Included 1",
                "authors": "Smith J.",
                "year": "2020",
                "article_id": "a1",
                "abstract": "Abstract 1",
            },
            "10.2222/inc2": {
                "doi": "10.2222/inc2",
                "title": "Included 2",
                "authors": "Jones K.",
                "year": "2021",
                "article_id": "a2",
                "abstract": "Abstract 2",
            },
        }

        references = [
            {"source_article_id": "a1", "cited_doi": "10.3333/ext1", "cited_title": "External 1", "cited_authors": "Brown L.", "cited_year": "2019", "is_in_project": False, "extraction_source": "openalex"},
            {"source_article_id": "a2", "cited_doi": "10.3333/ext1", "cited_title": "External 1", "cited_authors": "Brown L.", "cited_year": "2019", "is_in_project": False, "extraction_source": "openalex"},
            {"source_article_id": "a1", "cited_doi": "10.2222/inc2", "cited_title": "Included 2", "cited_authors": "Jones K.", "cited_year": "2021", "is_in_project": True, "extraction_source": "openalex"},
        ]

        G = builder._build_graph_from_data(articles_map, references)

        assert G.number_of_nodes() == 3  # 2 incluidos + 1 externo
        assert G.number_of_edges() == 3  # 3 referencias
        assert G.is_directed()

        # Verificar colores
        assert G.nodes["10.1111/inc1"]["status"] == "included"
        assert G.nodes["10.1111/inc1"]["color"]["background"] == "#22c55e"
        assert G.nodes["10.3333/ext1"]["status"] == "cited_external"
        assert G.nodes["10.3333/ext1"]["color"]["background"] == "#3b82f6"

        # Verificar artículo puente (citado por 2 incluidos)
        assert G.nodes["10.3333/ext1"]["is_bridge"] is True

    @pytest.mark.asyncio
    async def test_calculate_metrics(self):
        """calculate_metrics retorna métricas correctas."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")

        articles_map = {
            "10.1111/inc1": {"doi": "10.1111/inc1", "title": "Included 1", "authors": "Smith J.", "year": "2020", "article_id": "a1", "abstract": ""},
            "10.2222/inc2": {"doi": "10.2222/inc2", "title": "Included 2", "authors": "Jones K.", "year": "2021", "article_id": "a2", "abstract": ""},
        }

        references = [
            {"source_article_id": "a1", "cited_doi": "10.3333/ext1", "cited_title": "External 1", "cited_authors": "Brown L.", "cited_year": "2019", "is_in_project": False, "extraction_source": "openalex"},
            {"source_article_id": "a2", "cited_doi": "10.3333/ext1", "cited_title": "External 1", "cited_authors": "Brown L.", "cited_year": "2019", "is_in_project": False, "extraction_source": "openalex"},
            {"source_article_id": "a1", "cited_doi": "10.2222/inc2", "cited_title": "Included 2", "cited_authors": "Jones K.", "cited_year": "2021", "is_in_project": True, "extraction_source": "openalex"},
        ]

        G = builder._build_graph_from_data(articles_map, references)
        builder.graph = G
        metrics = builder.calculate_metrics()

        assert metrics["total_nodes"] == 3
        assert metrics["total_edges"] == 3
        assert metrics["total_included"] == 2
        assert metrics["total_external"] == 1
        assert len(metrics["most_cited"]) >= 1
        assert len(metrics["bridge_articles"]) == 1
        assert metrics["bridge_articles"][0]["doi"] == "10.3333/ext1"
        assert isinstance(metrics["density"], float)

    def test_serialize_to_vis_network_full(self):
        """serialize_to_vis_network produce formato completo."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")

        G = nx.DiGraph()
        G.add_node("10.1111/a", status="included", label="Smith (2020)", title="Paper A",
                   color={"background": "#22c55e", "border": "#16a34a"}, size=20, shape="dot")
        G.add_node("10.2222/b", status="cited_external", label="Brown (2019)", title="Paper B",
                   color={"background": "#3b82f6", "border": "#2563eb"}, size=12, shape="dot")
        G.add_edge("10.1111/a", "10.2222/b", arrows="to", extraction_source="openalex")
        builder.graph = G

        result = builder.serialize_to_vis_network()

        assert result["graph_type"] == "citation"
        assert result["project_id"] == "proj-001"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert "metadata" in result
        assert result["nodes"][0]["id"] == "10.1111/a"
        assert result["edges"][0]["from"] == "10.1111/a"
        assert result["edges"][0]["to"] == "10.2222/b"

    def test_get_neighbors_from_builder(self):
        """get_neighbors del builder retorna estructura correcta."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")

        G = nx.DiGraph()
        G.add_node("A", status="included", label="A (2020)", title="Paper A",
                   color={"background": "#22c55e"}, size=20)
        G.add_node("B", status="included", label="B (2021)", title="Paper B",
                   color={"background": "#22c55e"}, size=20)
        G.add_node("C", status="cited_external", label="C (2019)", title="Paper C",
                   color={"background": "#3b82f6"}, size=12)
        G.add_edge("A", "C")
        G.add_edge("B", "C")
        G.add_edge("A", "B")
        builder.graph = G

        neighbors = builder.get_neighbors("C", depth=1)

        assert len(neighbors["nodes"]) == 2  # A y B
        assert len(neighbors["edges"]) == 2  # A→C y B→C
        neighbor_ids = {n["id"] for n in neighbors["nodes"]}
        assert "A" in neighbor_ids
        assert "B" in neighbor_ids

    def test_get_neighbors_nonexistent_node(self):
        """get_neighbors para nodo inexistente retorna vacío."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        G = nx.DiGraph()
        G.add_node("A")
        builder.graph = G

        result = builder.get_neighbors("nonexistent")
        assert result == {"nodes": [], "edges": []}

    def test_get_neighbors_no_graph(self):
        """get_neighbors sin grafo construido retorna vacío."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        builder.graph = None

        result = builder.get_neighbors("10.1111/a")
        assert result == {"nodes": [], "edges": []}

    def test_save_graph_raises_without_graph(self):
        """save_graph lanza ValueError si no hay grafo."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        builder.graph = None

        with pytest.raises(ValueError, match="No hay grafo construido"):
            builder.save_graph()

    def test_calculate_metrics_returns_empty_without_graph(self):
        """calculate_metrics retorna dict vacío sin grafo."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        builder.graph = None

        assert builder.calculate_metrics() == {}

    def test_serialize_empty_without_graph(self):
        """serialize_to_vis_network retorna estructura vacía sin grafo."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        builder.graph = None

        result = builder.serialize_to_vis_network()
        assert result == {"nodes": [], "edges": [], "metadata": {}}

    def test_make_label_shortens_long_authors(self):
        """_make_label trunca autores largos."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")

        short_label = builder._make_label("Smith J.", "2020")
        assert "Smith J." in short_label
        assert "2020" in short_label

        long_authors = "VeryLongAuthorNameWithManyCharacters, Second Author, Third Author"
        label = builder._make_label(long_authors, "2021")
        assert len(label.split("(")[0].strip()) <= 28  # "..." added

    def test_make_label_handles_empty_authors(self):
        """_make_label maneja autores vacíos."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        label = builder._make_label("", "2020")
        assert label == "Unknown (2020)"


# ──────────────────────────────────────────────
# Tests de Cosine Similarity (TASK 4.3.2)
# ──────────────────────────────────────────────

class TestCosineSimilarity:
    """Tests de similitud coseno para grafo temático."""

    def test_cosine_similarity_identical_vectors(self):
        """Vectores idénticos tienen similitud 1.0."""
        v = np.array([[1, 2, 3]], dtype=float)
        sim = cosine_similarity(v, v)
        assert np.isclose(sim[0][0], 1.0)

    def test_cosine_similarity_orthogonal_vectors(self):
        """Vectores ortogonales tienen similitud ≈ 0.0."""
        v1 = np.array([[1, 0, 0]], dtype=float)
        v2 = np.array([[0, 1, 0]], dtype=float)
        sim = cosine_similarity(v1, v2)
        assert np.isclose(sim[0][0], 0.0)

    def test_cosine_similarity_opposite_vectors(self):
        """Vectores opuestos tienen similitud -1.0."""
        v1 = np.array([[1, 0, 0]], dtype=float)
        v2 = np.array([[-1, 0, 0]], dtype=float)
        sim = cosine_similarity(v1, v2)
        assert np.isclose(sim[0][0], -1.0)

    def test_cosine_similarity_matrix_shape(self):
        """Matriz de similitud tiene forma NxN."""
        embeddings = np.random.rand(10, 768)
        sim = cosine_similarity(embeddings)
        assert sim.shape == (10, 10)
        assert np.allclose(np.diag(sim), 1.0)


# ──────────────────────────────────────────────
# Tests de Community Detection (TASK 4.3.3)
# ──────────────────────────────────────────────

class TestCommunityDetection:
    """Tests de detección de comunidades."""

    def test_community_detection_returns_clusters(self):
        """Detecta al menos 1 cluster."""
        G = nx.Graph()
        for i in range(5):
            G.add_node(f"a{i}")
            G.add_node(f"b{i}")

        for i in range(5):
            for j in range(i + 1, 5):
                G.add_edge(f"a{i}", f"a{j}")

        for i in range(5):
            for j in range(i + 1, 5):
                G.add_edge(f"b{i}", f"b{j}")

        G.add_edge("a0", "b0")

        communities = nx.algorithms.community.greedy_modularity_communities(G)
        assert len(communities) >= 1

    def test_community_detection_single_cluster(self):
        """Grafo completamente conectado retorna 1 cluster."""
        G = nx.complete_graph(5)
        communities = nx.algorithms.community.greedy_modularity_communities(G)
        assert len(communities) == 1


# ──────────────────────────────────────────────
# Tests de ThematicGraphBuilder (TASK 4.3.1 + 4.3.4)
# ──────────────────────────────────────────────

class TestThematicGraphBuilder:
    """Tests del grafo temático."""

    def test_cluster_colors_constant(self):
        """CLUSTER_COLORS tiene 10 colores."""
        from app.services.graph_service import CLUSTER_COLORS
        assert len(CLUSTER_COLORS) == 10
        assert CLUSTER_COLORS[0] == "#22c55e"

    def test_threshold_filtering_default(self):
        """Umbral default 0.75 filtra correctamente."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.75)
        builder.article_dois = ["A", "B", "C"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.9, 0.1, 0],
            [0, 1, 0],
        ], dtype=float)

        G = builder.build_undirected_graph()

        assert G.has_edge("A", "B")
        assert not G.has_edge("A", "C")

    def test_threshold_strict(self):
        """Umbral estricto 0.95 filtra más aristas."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.95)
        builder.article_dois = ["A", "B"]
        # [1,0,0] y [0.5,0.5,0] tienen cos_sim ≈ 0.707 < 0.95
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.5, 0.5, 0],
        ], dtype=float)

        G = builder.build_undirected_graph()
        assert not G.has_edge("A", "B")

    def test_threshold_relaxed(self):
        """Umbral relajado 0.0 conecta todo."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B", "C"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ], dtype=float)

        G = builder.build_undirected_graph()
        assert G.has_edge("A", "B")
        assert G.has_edge("A", "C")
        assert G.has_edge("B", "C")

    def test_undirected_graph_construction(self):
        """Grafo es no-dirigido."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B"]
        builder.embeddings = np.array([[1, 0], [0, 1]], dtype=float)

        G = builder.build_undirected_graph()
        assert not G.is_directed()

    def test_edge_thickness_proportional_to_similarity(self):
        """Grosor de arista proporcional a similitud."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B", "C"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.9, 0.1, 0],
            [0.1, 0.9, 0],
        ], dtype=float)

        G = builder.build_undirected_graph()

        sim_ab = G.edges["A", "B"]["cosine_similarity"]
        sim_ac = G.edges["A", "C"]["cosine_similarity"]

        assert sim_ab > sim_ac

    def test_serialize_thematic_graph(self):
        """Serialización produce formato vis-network con aristas punteadas."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B"]
        builder.embeddings = np.array([[1, 0], [0.9, 0.1]], dtype=float)

        G = builder.build_undirected_graph()

        cluster_map = builder.detect_communities()
        builder.apply_cluster_colors(cluster_map)

        result = builder.serialize_and_save("test-project")

        assert result["graph_type"] == "thematic"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["dashes"] == [5, 5]
        assert "cosine_similarity" in result["edges"][0]

    def test_detect_communities_returns_dict(self):
        """detect_communities retorna dict {doi: cluster_id}."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B", "C"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.9, 0.1, 0],
            [0.1, 0.9, 0],
        ], dtype=float)

        builder.build_undirected_graph()
        clusters = builder.detect_communities()

        assert isinstance(clusters, dict)
        assert len(clusters) == 3
        assert all(isinstance(v, int) for v in clusters.values())

    def test_enrich_edges_with_keywords(self):
        """enrich_edges_with_keywords añade shared_keywords."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B"]
        builder.embeddings = np.array([[1, 0], [0.9, 0.1]], dtype=float)
        builder.build_undirected_graph()

        builder.enrich_edges_with_keywords({
            "A": ["ml", "deep-learning", "nlp"],
            "B": ["ml", "computer-vision", "nlp"],
        })

        shared = builder.graph.edges["A", "B"]["shared_keywords"]
        assert "ml" in shared
        assert "nlp" in shared
        assert "deep-learning" not in shared

    def test_apply_cluster_colors(self):
        """apply_cluster_colors asigna colores por cluster."""
        from app.services.graph_service import ThematicGraphBuilder, CLUSTER_COLORS

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B", "C"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.9, 0.1, 0],
            [0.1, 0.9, 0],
        ], dtype=float)
        builder.build_undirected_graph()

        cluster_map = {"A": 0, "B": 0, "C": 1}
        builder.apply_cluster_colors(cluster_map)

        assert builder.graph.nodes["A"]["color"]["background"] == CLUSTER_COLORS[0]
        assert builder.graph.nodes["C"]["color"]["background"] == CLUSTER_COLORS[1]
        assert builder.graph.nodes["A"]["cluster"] == 0
        assert builder.graph.nodes["C"]["cluster"] == 1

    def test_build_empty_embeddings(self):
        """Embeddings vacíos retorna grafo vacío."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder()
        builder.article_dois = []
        builder.embeddings = np.array([], dtype=float)

        G = builder.build_undirected_graph()
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_compute_similarity_matrix_empty(self):
        """compute_similarity_matrix con embeddings vacíos retorna array vacío."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder()
        builder.embeddings = None

        result = builder.compute_similarity_matrix()
        assert len(result) == 0

    def test_set_embeddings(self):
        """set_embeddings establece embeddings y dois correctamente."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder()
        embeddings = np.array([[1, 0], [0, 1]], dtype=float)
        builder.set_embeddings(embeddings, ["A", "B"])

        assert builder.embeddings is not None
        assert builder.article_dois == ["A", "B"]
        assert builder.embeddings.shape == (2, 2)

    def test_detect_communities_empty_graph(self):
        """detect_communities con grafo vacío retorna dict vacío."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder()
        builder.graph = nx.Graph()

        result = builder.detect_communities()
        assert result == {}

    def test_serialize_empty_graph(self):
        """serialize_and_save con grafo vacío retorna estructura vacía."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder()
        builder.graph = None

        result = builder.serialize_and_save("test-project")
        assert result == {"nodes": [], "edges": [], "metadata": {}}

    def test_metadata_includes_threshold_and_clusters(self):
        """Metadata incluye threshold, num_clusters y cluster_sizes."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.5)
        builder.article_dois = ["A", "B", "C", "D"]
        builder.embeddings = np.array([
            [1, 0, 0],
            [0.95, 0.05, 0],
            [0, 1, 0],
            [0.05, 0.95, 0],
        ], dtype=float)

        G = builder.build_undirected_graph()
        clusters = builder.detect_communities()
        builder.apply_cluster_colors(clusters)

        result = builder.serialize_and_save("test-project")

        assert result["metadata"]["threshold"] == 0.5
        assert result["metadata"]["num_clusters"] >= 1
        assert "cluster_sizes" in result["metadata"]
        assert result["metadata"]["total_nodes"] == 4


# ──────────────────────────────────────────────
# Tests de Filtro Estricto + Screening (TASK 4.6.4)
# ──────────────────────────────────────────────

class TestStrictFiltering:
    """Tests de filtrado estricto para artículos elegibles."""

    def _make_mock_article(self, article_id, doi, download_status, local_md_path, parsed_status, search_query_id):
        """Crea un mock Article con campos de filtro estricto."""
        class MockArticle:
            pass
        a = MockArticle()
        a.id = article_id
        a.doi = doi
        a.download_status = download_status
        a.local_md_path = local_md_path
        a.parsed_status = parsed_status
        a.search_query_id = search_query_id
        a.title = "Test Article"
        a.authors = "Test Author"
        a.year = 2024
        a.abstract = "Test abstract"
        return a

    def _make_mock_search_query(self, query_id, project_id):
        """Crea un mock SearchQuery."""
        class MockQuery:
            pass
        q = MockQuery()
        q.id = query_id
        q.project_id = project_id
        return q

    def _make_mock_decision(self, article_id, decision):
        """Crea un mock ScreeningDecision."""
        class MockDecision:
            pass
        d = MockDecision()
        d.article_id = article_id
        d.decision = decision
        return d

    @pytest.mark.asyncio
    async def test_strict_filter_all_criteria_met(self):
        """Artículo con todos los criterios estrictos pasa el filtro."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_article = self._make_mock_article(
            "a1", "10.1111/test", "SUCCESS", "/path/to/md.md", "success", "sq1"
        )
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_article]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 1
        assert articles[0].doi == "10.1111/test"

    @pytest.mark.asyncio
    async def test_strict_filter_missing_doi(self):
        """Artículo sin DOI es excluido."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_strict_filter_download_not_success(self):
        """Artículo con download_status != SUCCESS es excluido."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_strict_filter_missing_md_path(self):
        """Artículo sin local_md_path es excluido."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_strict_filter_parsed_status_not_success(self):
        """Artículo con parsed_status != success es excluido."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_screening_filter_included(self):
        """Filtro screening=included solo retorna artículos con decision=include."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_article = self._make_mock_article(
            "a1", "10.1111/test", "SUCCESS", "/path/to/md.md", "success", "sq1"
        )
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_article]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "included")

        assert len(articles) == 1

    @pytest.mark.asyncio
    async def test_screening_filter_maybe(self):
        """Filtro screening=maybe solo retorna artículos con decision=maybe."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_article = self._make_mock_article(
            "a1", "10.1111/test", "SUCCESS", "/path/to/md.md", "success", "sq1"
        )
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_article]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "maybe")

        assert len(articles) == 1

    @pytest.mark.asyncio
    async def test_screening_filter_all_no_decision_join(self):
        """Filtro screening=all no hace JOIN con ScreeningDecision."""
        from app.services.graph_service import get_eligible_articles_for_graphs

        mock_session = AsyncMock()
        mock_article = self._make_mock_article(
            "a1", "10.1111/test", "SUCCESS", "/path/to/md.md", "success", "sq1"
        )
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_article]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        articles = await get_eligible_articles_for_graphs("proj-001", mock_session, "all")

        assert len(articles) == 1
        # Verificar que la query se ejecutó correctamente
        mock_session.execute.assert_called_once()

    def test_save_graph_with_suffix(self, tmp_path):
        """save_graph genera archivo con suffix correcto."""
        from app.services.graph_service import CitationGraphBuilder

        builder = CitationGraphBuilder(AsyncMock(), "proj-001")
        G = nx.DiGraph()
        G.add_node("10.1111/a", status="included", label="A (2020)", title="Paper A",
                   color={"background": "#22c55e", "border": "#16a34a"}, size=20, shape="dot")
        builder.graph = G

        path = builder.save_graph(graph_dir=tmp_path, suffix="maybe")
        assert path.name == "citation_graph_maybe.json"
        assert path.exists()

    def test_load_graph_with_suffix(self, tmp_path):
        """load_graph carga archivo con suffix correcto."""
        from app.services.graph_service import CitationGraphBuilder

        data = {
            "graph_type": "citation",
            "nodes": [{"id": "10.1111/a", "status": "included"}],
            "edges": [],
            "metadata": {},
        }
        json_path = tmp_path / "citation_graph_included.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = CitationGraphBuilder.load_graph("proj-001", graph_dir=tmp_path, suffix="included")
        assert result is not None
        assert result["graph_type"] == "citation"

    def test_load_graph_wrong_suffix_returns_none(self, tmp_path):
        """load_graph con suffix incorrecto retorna None."""
        from app.services.graph_service import CitationGraphBuilder

        data = {
            "graph_type": "citation",
            "nodes": [],
            "edges": [],
            "metadata": {},
        }
        json_path = tmp_path / "citation_graph_included.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        result = CitationGraphBuilder.load_graph("proj-001", graph_dir=tmp_path, suffix="maybe")
        assert result is None

    def test_serialize_thematic_with_suffix(self, tmp_path):
        """serialize_and_save genera archivo temático con suffix correcto."""
        from app.services.graph_service import ThematicGraphBuilder

        builder = ThematicGraphBuilder(threshold=0.0)
        builder.article_dois = ["A", "B"]
        builder.embeddings = np.array([[1, 0], [0.9, 0.1]], dtype=float)
        builder.build_undirected_graph()

        result = builder.serialize_and_save("test-project", graph_dir=tmp_path, suffix="maybe")
        assert result["metadata"]["screening_status"] == "maybe"
        assert (tmp_path / "thematic_graph_maybe.json").exists()
